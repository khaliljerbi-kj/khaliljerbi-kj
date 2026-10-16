"""Geometric Brownian Motion Monte Carlo projections.

    dS_t = mu * S_t dt + sigma * S_t dW_t
    S_t  = S_0 * exp((mu - sigma²/2) t + sigma W_t)

Paths use the exact log-normal discretisation (no Euler bias) with antithetic
variates. Three macro scenarios shift the drift (interest-rate / demand shocks)
and scale the volatility; each scenario's curve is the median of its paths, and
the fan bands come from the central scenario's percentiles.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
from scipy import stats

LONG_RUN_DRIFT = 0.020  # Long-run nominal appreciation of Paris residential (≈ inflation).
LONG_RUN_VOL = 0.050
HISTORY_WEIGHT = 0.35  # Shrinkage of the local 5y calibration towards long-run values.
RATE_BETA = 2.0  # Annual drift change per +1pp of mortgage rates (price elasticity).


@dataclass(frozen=True)
class Scenario:
    key: str
    label: str
    description: str
    rate_shock_pp: float  # Change in mortgage rates, percentage points.
    demand_shift: float  # Additional annual drift from demand (supply/demand imbalance).
    vol_multiplier: float


SCENARIOS: tuple[Scenario, ...] = (
    Scenario(
        "pessimistic",
        "Pessimiste",
        "Hausse des taux (+1,5 pt) et baisse de la demande solvable.",
        rate_shock_pp=1.5,
        demand_shift=-0.005,
        vol_multiplier=1.35,
    ),
    Scenario(
        "median",
        "Médian",
        "Prolongement de la tendance de marché, taux stables.",
        rate_shock_pp=0.0,
        demand_shift=0.0,
        vol_multiplier=1.0,
    ),
    Scenario(
        "optimistic",
        "Optimiste",
        "Baisse des taux (-1 pt) et forte demande.",
        rate_shock_pp=-1.0,
        demand_shift=0.005,
        vol_multiplier=1.10,
    ),
)


@dataclass(frozen=True)
class ScenarioParams:
    key: str
    label: str
    description: str
    mu: float
    sigma: float


def scenario_params(hist_mu: float, hist_sigma: float) -> list[ScenarioParams]:
    """Blend the local calibration with long-run values, then apply macro shocks."""
    base_mu = HISTORY_WEIGHT * hist_mu + (1 - HISTORY_WEIGHT) * LONG_RUN_DRIFT
    base_sigma = HISTORY_WEIGHT * hist_sigma + (1 - HISTORY_WEIGHT) * LONG_RUN_VOL
    params = []
    for s in SCENARIOS:
        mu = base_mu - RATE_BETA * s.rate_shock_pp / 100 + s.demand_shift
        params.append(ScenarioParams(s.key, s.label, s.description, mu, base_sigma * s.vol_multiplier))
    return params


def simulate_gbm(
    s0: float,
    mu: float,
    sigma: float,
    years: float = 10.0,
    steps_per_year: int = 12,
    n_paths: int = 4_000,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """Simulated price paths, shape (n_paths, n_steps + 1); column 0 is s0."""
    if s0 <= 0 or sigma < 0 or n_paths < 2:
        raise ValueError("s0 must be > 0, sigma >= 0 and n_paths >= 2")
    rng = rng or np.random.default_rng()
    n_steps = int(round(years * steps_per_year))
    dt = 1.0 / steps_per_year

    half = (n_paths + 1) // 2
    z = rng.standard_normal((half, n_steps))
    z = np.concatenate([z, -z])[:n_paths]  # Antithetic variates.

    log_increments = (mu - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * z
    log_paths = np.concatenate([np.zeros((n_paths, 1)), np.cumsum(log_increments, axis=1)], axis=1)
    return s0 * np.exp(log_paths)


def prob_loss(mu: float, sigma: float, t: float) -> float:
    """Analytic P(S_t < S_0) under GBM."""
    if t <= 0:
        return 0.0
    drift = (mu - 0.5 * sigma**2) * t
    if sigma == 0:
        return float(drift < 0)
    return float(stats.norm.cdf(-drift / (sigma * np.sqrt(t))))


def value_at_risk(mu: float, sigma: float, t: float, level: float = 0.95) -> float:
    """Analytic relative VaR at horizon t: loss not exceeded with probability `level`."""
    if t <= 0 or sigma == 0:
        return max(0.0, -float(np.expm1(mu * t)))
    q = stats.lognorm.ppf(1 - level, s=sigma * np.sqrt(t), scale=np.exp((mu - 0.5 * sigma**2) * t))
    return float(max(0.0, 1.0 - q))


def project(
    s0: float,
    hist_mu: float,
    hist_sigma: float,
    years: int = 10,
    steps_per_year: int = 12,
    n_paths: int = 4_000,
    seed: int = 0,
    horizons: tuple[int, ...] = (1, 5, 10),
    output_every: int = 3,
) -> dict:
    """Run the three scenarios and assemble chart-ready projections."""
    params = scenario_params(hist_mu, hist_sigma)
    rng = np.random.default_rng(seed)
    paths = {
        p.key: simulate_gbm(s0, p.mu, p.sigma, years, steps_per_year, n_paths, rng)
        for p in params
    }

    t = np.arange(paths["median"].shape[1]) / steps_per_year
    idx = np.arange(0, len(t), output_every)  # Quarterly output by default.
    medians = {k: np.median(v, axis=0) for k, v in paths.items()}
    bands = np.percentile(paths["median"], [5, 25, 75, 95], axis=0)

    points = [
        {
            "t": round(float(t[i]), 4),
            "pessimistic": round(float(medians["pessimistic"][i])),
            "median": round(float(medians["median"][i])),
            "optimistic": round(float(medians["optimistic"][i])),
            "p5": round(float(bands[0, i])),
            "p25": round(float(bands[1, i])),
            "p75": round(float(bands[2, i])),
            "p95": round(float(bands[3, i])),
        }
        for i in idx
    ]

    by_key = {p.key: p for p in params}
    summary = []
    for h in horizons:
        i = int(h * steps_per_year)
        row = {"years": h}
        for k, med in medians.items():
            row[k] = round(float(med[i]))
            row[f"{k}_cagr"] = round(float((med[i] / s0) ** (1 / h) - 1), 5)
        m = by_key["median"]
        row["prob_loss"] = round(prob_loss(m.mu, m.sigma, h), 4)
        row["var95"] = round(value_at_risk(m.mu, m.sigma, h), 4)
        summary.append(row)

    return {
        "points": points,
        "horizons": summary,
        "scenarios": [asdict(p) for p in params],
        "n_paths": n_paths,
        "steps_per_year": steps_per_year,
    }
