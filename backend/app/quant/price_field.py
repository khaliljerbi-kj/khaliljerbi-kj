"""Mock spatial price model for Paris (EUR/m²).

Until real DVF transactions are wired in, the current price at a point is a smooth
kernel interpolation between arrondissement-level reference prices, plus a small
deterministic high-frequency texture. A per-street premium (stable hash of the
street name) is added for point estimates. Every output is clipped to the
[7 000, 15 000] €/m² band required by the spec.
"""

from __future__ import annotations

import hashlib
import unicodedata
from dataclasses import dataclass

import numpy as np

PRICE_MIN = 7_000.0
PRICE_MAX = 15_000.0

PARIS_CENTER = (48.8566, 2.3522)

# Bounding box of Paris intra-muros (lat_min, lat_max, lon_min, lon_max).
PARIS_BBOX = (48.815, 48.905, 2.224, 2.470)


@dataclass(frozen=True)
class Arrondissement:
    number: int
    lat: float
    lon: float
    price_m2: float  # Indicative 2025-2026 average sale price, €/m².


# Centroids of the built-up part of each arrondissement and indicative prices.
ARRONDISSEMENTS: tuple[Arrondissement, ...] = (
    Arrondissement(1, 48.8625, 2.3364, 13_400),
    Arrondissement(2, 48.8683, 2.3428, 11_800),
    Arrondissement(3, 48.8630, 2.3601, 12_700),
    Arrondissement(4, 48.8543, 2.3576, 13_200),
    Arrondissement(5, 48.8445, 2.3497, 12_300),
    Arrondissement(6, 48.8491, 2.3328, 14_700),
    Arrondissement(7, 48.8562, 2.3121, 14_100),
    Arrondissement(8, 48.8727, 2.3125, 12_100),
    Arrondissement(9, 48.8770, 2.3375, 11_000),
    Arrondissement(10, 48.8761, 2.3607, 9_800),
    Arrondissement(11, 48.8590, 2.3800, 10_300),
    Arrondissement(12, 48.8402, 2.3889, 9_600),
    Arrondissement(13, 48.8283, 2.3622, 8_900),
    Arrondissement(14, 48.8292, 2.3266, 10_000),
    Arrondissement(15, 48.8401, 2.2928, 10_100),
    Arrondissement(16, 48.8635, 2.2750, 11_600),
    Arrondissement(17, 48.8873, 2.3067, 10_700),
    Arrondissement(18, 48.8925, 2.3484, 9_300),
    Arrondissement(19, 48.8871, 2.3848, 8_200),
    Arrondissement(20, 48.8634, 2.4011, 8_600),
)

_ARR_LAT = np.array([a.lat for a in ARRONDISSEMENTS])
_ARR_LON = np.array([a.lon for a in ARRONDISSEMENTS])
_ARR_PRICE = np.array([a.price_m2 for a in ARRONDISSEMENTS])

# Kilometres per degree at Paris' latitude.
_KM_PER_DEG_LAT = 111.2
_KM_PER_DEG_LON = 111.2 * np.cos(np.radians(PARIS_CENTER[0]))
_KERNEL_BANDWIDTH_KM = 1.1

# A few well-known streets, so `/api/estimate?street=...` works without a geocoder.
KNOWN_STREETS: dict[str, tuple[float, float]] = {
    "rue de rivoli": (48.8606, 2.3376),
    "avenue des champs-elysees": (48.8698, 2.3078),
    "boulevard saint-germain": (48.8530, 2.3360),
    "rue de la paix": (48.8692, 2.3310),
    "avenue montaigne": (48.8661, 2.3044),
    "avenue foch": (48.8718, 2.2850),
    "boulevard haussmann": (48.8738, 2.3320),
    "rue de rennes": (48.8470, 2.3289),
    "rue de vaugirard": (48.8434, 2.3080),
    "rue mouffetard": (48.8418, 2.3497),
    "rue oberkampf": (48.8652, 2.3780),
    "rue du faubourg saint-antoine": (48.8509, 2.3820),
    "boulevard de belleville": (48.8705, 2.3790),
    "rue de menilmontant": (48.8682, 2.3930),
    "rue lepic": (48.8858, 2.3354),
    "rue de la roquette": (48.8569, 2.3770),
}


def normalize_street(name: str) -> str:
    """Lower-case, accent-free, single-spaced street name."""
    decomposed = unicodedata.normalize("NFKD", name)
    ascii_only = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join(ascii_only.lower().replace("’", "'").split())


def stable_seed(*parts: object) -> int:
    """Deterministic 32-bit seed (Python's hash() is salted per process)."""
    digest = hashlib.sha256("|".join(str(p) for p in parts).encode()).digest()
    return int.from_bytes(digest[:4], "little")


def street_location(street: str) -> tuple[float, float]:
    """Coordinates of a known street, or a stable pseudo-location inside Paris."""
    key = normalize_street(street)
    if key in KNOWN_STREETS:
        return KNOWN_STREETS[key]
    rng = np.random.default_rng(stable_seed("street-loc", key))
    lat = PARIS_CENTER[0] + rng.uniform(-0.025, 0.025)
    lon = PARIS_CENTER[1] + rng.uniform(-0.05, 0.05)
    return float(lat), float(lon)


def nearest_arrondissement(lat: float, lon: float) -> Arrondissement:
    d2 = ((_ARR_LAT - lat) * _KM_PER_DEG_LAT) ** 2 + ((_ARR_LON - lon) * _KM_PER_DEG_LON) ** 2
    return ARRONDISSEMENTS[int(np.argmin(d2))]


def base_price_field(lat: np.ndarray | float, lon: np.ndarray | float) -> np.ndarray:
    """Smooth €/m² surface (vectorised): Gaussian-kernel interpolation + texture."""
    lat = np.asarray(lat, dtype=float)
    lon = np.asarray(lon, dtype=float)
    dy = (lat[..., None] - _ARR_LAT) * _KM_PER_DEG_LAT
    dx = (lon[..., None] - _ARR_LON) * _KM_PER_DEG_LON
    weights = np.exp(-(dx**2 + dy**2) / (2 * _KERNEL_BANDWIDTH_KM**2)) + 1e-12
    smooth = (weights * _ARR_PRICE).sum(axis=-1) / weights.sum(axis=-1)

    # Deterministic micro-market texture (±4%): a few incommensurate waves.
    texture = (
        0.020 * np.sin(lat * 900.0 + lon * 310.0)
        + 0.012 * np.sin(lat * 1_700.0 - lon * 1_100.0 + 1.3)
        + 0.008 * np.cos(lon * 2_300.0 + 0.7)
    )
    return np.clip(smooth * (1.0 + texture), PRICE_MIN, PRICE_MAX)


def street_premium(street: str | None) -> float:
    """Stable multiplicative premium in [-5%, +5%] attached to a street name."""
    if not street:
        return 1.0
    rng = np.random.default_rng(stable_seed("street-premium", normalize_street(street)))
    return float(1.0 + rng.uniform(-0.05, 0.05))


def estimate_price(lat: float, lon: float, street: str | None = None) -> float:
    price = float(base_price_field(lat, lon)) * street_premium(street)
    return float(np.clip(price, PRICE_MIN, PRICE_MAX))


def price_grid(n_lat: int = 90, n_lon: int = 120) -> dict:
    """Regular grid of the smooth surface over Paris, used by the map heatmap."""
    lat_min, lat_max, lon_min, lon_max = PARIS_BBOX
    lats = np.linspace(lat_min, lat_max, n_lat)
    lons = np.linspace(lon_min, lon_max, n_lon)
    grid = base_price_field(*np.meshgrid(lats, lons, indexing="ij"))
    return {
        "lat_min": lat_min,
        "lat_max": lat_max,
        "lon_min": lon_min,
        "lon_max": lon_max,
        "n_lat": n_lat,
        "n_lon": n_lon,
        # Row-major, row 0 = lat_min.
        "values": np.rint(grid).astype(int).ravel().tolist(),
        "min": PRICE_MIN,
        "max": PRICE_MAX,
    }
