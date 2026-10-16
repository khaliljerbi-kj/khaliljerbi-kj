"""FastAPI entry point: `uvicorn app.main:app --reload --port 8000`."""

from __future__ import annotations

import os
from datetime import date
from functools import lru_cache

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .quant import gbm, history, price_field
from .schemas import EstimateRequest, EstimateResponse, PriceGrid

app = FastAPI(
    title="Immo Quant Paris",
    version="0.1.0",
    description="Estimation du prix au m² (mock DVF) et projections Monte Carlo (GBM).",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Accept clicks slightly outside the city limits (périphérique, bois).
_MARGIN = 0.03


def _in_paris(lat: float, lon: float) -> bool:
    lat_min, lat_max, lon_min, lon_max = price_field.PARIS_BBOX
    return lat_min - _MARGIN <= lat <= lat_max + _MARGIN and lon_min - _MARGIN <= lon <= lon_max + _MARGIN


def _projection_label(start: pd.Period, t: float) -> str:
    p = start + int(round(t * 4))
    return f"{p.year}-T{p.quarter}"


def run_estimate(req: EstimateRequest, today: date | None = None) -> EstimateResponse:
    today = today or date.today()
    street = req.street.strip() if req.street and req.street.strip() else None
    if req.lat is not None and req.lon is not None:
        lat, lon = req.lat, req.lon
    else:
        lat, lon = price_field.street_location(street or "")

    if not _in_paris(lat, lon):
        raise HTTPException(status_code=422, detail="Coordonnées hors de Paris.")

    arr = price_field.nearest_arrondissement(lat, lon)
    current = price_field.estimate_price(lat, lon, street)
    # Same point + street => same numbers on every call.
    seed = price_field.stable_seed(round(lat, 4), round(lon, 4), price_field.normalize_street(street or ""))

    hist = history.build_history(current, seed=seed, today=today)
    hist_mu, hist_sigma = history.calibrate(hist)
    proj = gbm.project(current, hist_mu, hist_sigma, seed=seed)

    start = pd.Period(pd.Timestamp(today), freq="Q")
    suffix = "er" if arr.number == 1 else "e"
    return EstimateResponse(
        location={
            "lat": lat,
            "lon": lon,
            "street": street,
            "arrondissement": arr.number,
            "label": street or f"Paris {arr.number}{suffix}",
        },
        current_price_m2=round(current),
        history=[
            {"date": d.date().isoformat(), "label": label, "price": p}
            for d, label, p in hist[["date", "label", "price"]].itertuples(index=False)
        ],
        projection=[{**pt, "label": _projection_label(start, pt["t"])} for pt in proj["points"]],
        horizons=proj["horizons"],
        scenarios=proj["scenarios"],
        calibration={
            "hist_mu": round(hist_mu, 5),
            "hist_sigma": round(hist_sigma, 5),
            "n_paths": proj["n_paths"],
            "steps_per_year": proj["steps_per_year"],
            "seed": seed,
        },
    )


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/estimate", response_model=EstimateResponse)
def estimate_get(
    lat: float | None = Query(None, ge=-90, le=90),
    lon: float | None = Query(None, ge=-180, le=180),
    street: str | None = Query(None, max_length=200),
) -> EstimateResponse:
    try:
        req = EstimateRequest(lat=lat, lon=lon, street=street)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return run_estimate(req)


@app.post("/api/estimate", response_model=EstimateResponse)
def estimate_post(req: EstimateRequest) -> EstimateResponse:
    return run_estimate(req)


@lru_cache(maxsize=1)
def _grid() -> PriceGrid:
    return PriceGrid(**price_field.price_grid())


@app.get("/api/price-grid", response_model=PriceGrid)
def price_grid() -> PriceGrid:
    return _grid()
