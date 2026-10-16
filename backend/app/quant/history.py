"""Synthetic 5-year quarterly price history (stand-in for DVF aggregates).

The shape follows the Paris market cycle (2021-2022 peak, 2023-2024 correction
after the ECB rate hikes, 2025-2026 stabilisation), scaled so the last point is
the current local estimate, with a stable local beta and idiosyncratic noise.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

# Paris-wide index, relative to "now" = 1.00, sampled yearly going back 5 years.
# Index: years before today -> level.
_PARIS_CYCLE = {5.0: 1.045, 4.0: 1.085, 3.0: 1.060, 2.0: 0.985, 1.0: 0.975, 0.0: 1.000}


def quarter_label(ts: pd.Timestamp) -> str:
    return f"{ts.year}-T{ts.quarter}"


def build_history(current_price: float, seed: int, years: int = 5, today: date | None = None) -> pd.DataFrame:
    """Quarterly history ending at the current quarter. Columns: date, label, price."""
    today = today or date.today()
    end = pd.Period(pd.Timestamp(today), freq="Q")
    periods = pd.period_range(end=end, periods=years * 4 + 1, freq="Q")

    years_back = np.array([(end - p).n / 4.0 for p in periods])
    anchors_x = np.array(sorted(_PARIS_CYCLE))
    anchors_y = np.array([_PARIS_CYCLE[x] for x in anchors_x])
    paris_index = np.interp(years_back, anchors_x, anchors_y)

    rng = np.random.default_rng(seed)
    local_beta = rng.uniform(0.7, 1.3)  # Sensitivity of the micro-market to the city cycle.
    local_index = 1.0 + local_beta * (paris_index - 1.0)

    # Idiosyncratic noise as a random walk pinned to zero today (Brownian bridge-like).
    shocks = rng.normal(0.0, 0.008, size=len(periods))
    walk = np.cumsum(shocks)
    walk -= walk[-1]
    prices = current_price * local_index * np.exp(walk)
    prices[-1] = current_price

    return pd.DataFrame(
        {
            "date": periods.to_timestamp(how="end").normalize(),
            "label": [quarter_label(p.to_timestamp()) for p in periods],
            "price": np.round(prices, 0),
        }
    )


def calibrate(history: pd.DataFrame) -> tuple[float, float]:
    """Annualised drift and volatility from quarterly log returns."""
    log_returns = np.log(history["price"]).diff().dropna()
    periods_per_year = 4
    sigma = float(log_returns.std(ddof=1) * np.sqrt(periods_per_year))
    # GBM: E[log return] = (mu - sigma²/2) dt  =>  mu = mean/dt + sigma²/2
    mu = float(log_returns.mean() * periods_per_year + 0.5 * sigma**2)
    return mu, sigma
