from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class EstimateRequest(BaseModel):
    lat: float | None = Field(None, ge=-90, le=90)
    lon: float | None = Field(None, ge=-180, le=180)
    street: str | None = Field(None, max_length=200)

    @model_validator(mode="after")
    def _need_location(self) -> "EstimateRequest":
        has_coords = self.lat is not None and self.lon is not None
        if not has_coords and not (self.street and self.street.strip()):
            raise ValueError("Fournir `lat` et `lon`, ou `street`.")
        if (self.lat is None) != (self.lon is None):
            raise ValueError("`lat` et `lon` doivent être fournis ensemble.")
        return self


class Location(BaseModel):
    lat: float
    lon: float
    street: str | None
    arrondissement: int
    label: str


class HistoryPoint(BaseModel):
    date: str
    label: str
    price: float


class ProjectionPoint(BaseModel):
    t: float
    label: str
    pessimistic: float
    median: float
    optimistic: float
    p5: float
    p25: float
    p75: float
    p95: float


class ScenarioOut(BaseModel):
    key: str
    label: str
    description: str
    mu: float
    sigma: float


class HorizonSummary(BaseModel):
    years: int
    pessimistic: float
    median: float
    optimistic: float
    pessimistic_cagr: float
    median_cagr: float
    optimistic_cagr: float
    prob_loss: float
    var95: float


class Calibration(BaseModel):
    hist_mu: float
    hist_sigma: float
    n_paths: int
    steps_per_year: int
    seed: int


class EstimateResponse(BaseModel):
    location: Location
    current_price_m2: float
    currency: str = "EUR"
    history: list[HistoryPoint]
    projection: list[ProjectionPoint]
    horizons: list[HorizonSummary]
    scenarios: list[ScenarioOut]
    calibration: Calibration
    is_mock: bool = True


class PriceGrid(BaseModel):
    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float
    n_lat: int
    n_lon: int
    values: list[int]
    min: float
    max: float
