"""Temps de trajet porte-à-porte.

Google Distance Matrix (mode transit) si GOOGLE_MAPS_API_KEY est défini — Mapbox
ne gère pas les transports en commun, d'où ce choix. Sinon, estimation calibrée
sur le réseau RATP/RER pour garder le produit utilisable en développement.
"""

import logging
from dataclasses import dataclass
from functools import lru_cache

import httpx

from ..config import get_settings
from ..knowledge.paris import find_place, haversine_km
from ..schemas import TravelMode

log = logging.getLogger(__name__)

DISTANCE_MATRIX_URL = "https://maps.googleapis.com/maps/api/distancematrix/json"
GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"


@dataclass(frozen=True)
class LatLng:
    lat: float
    lng: float
    label: str


@lru_cache(maxsize=256)
def resolve_destination(query: str) -> LatLng | None:
    place = find_place(query)
    if place:
        return LatLng(place.lat, place.lng, place.nom)
    key = get_settings().google_maps_api_key
    if not key:
        return None
    try:
        r = httpx.get(
            GEOCODE_URL,
            params={"address": query, "region": "fr", "components": "country:FR", "key": key},
            timeout=5,
        )
        r.raise_for_status()
        results = r.json().get("results") or []
        if results:
            loc = results[0]["geometry"]["location"]
            return LatLng(loc["lat"], loc["lng"], results[0]["formatted_address"])
    except httpx.HTTPError as exc:
        log.warning("Géocodage Google indisponible : %s", exc)
    return None


def estimate_minutes(origin: tuple[float, float], dest: LatLng, mode: TravelMode) -> int:
    km = haversine_km(origin[0], origin[1], dest.lat, dest.lng)
    if mode == "walking":
        return round(km * 1.3 / 4.8 * 60)
    if mode == "bicycling":
        return round(km * 1.25 / 15 * 60) + 2
    # Transports en commun : marche + attente, puis vitesse commerciale métro
    # dans Paris (~20 km/h) et RER au-delà (~38 km/h).
    inner = min(km, 8.0)
    outer = max(km - 8.0, 0.0)
    return round(8 + inner * 3.0 + outer * 1.6)


def travel_minutes(
    origins: list[tuple[float, float]], dest: LatLng, mode: TravelMode
) -> tuple[list[int], bool]:
    """Renvoie (minutes par origine, estimé?). Un seul appel Distance Matrix par lot."""
    key = get_settings().google_maps_api_key
    if key and origins:
        try:
            minutes: list[int] = []
            for i in range(0, len(origins), 25):  # limite de 25 origines par requête
                batch = origins[i : i + 25]
                r = httpx.get(
                    DISTANCE_MATRIX_URL,
                    params={
                        "origins": "|".join(f"{lat},{lng}" for lat, lng in batch),
                        "destinations": f"{dest.lat},{dest.lng}",
                        "mode": mode,
                        "language": "fr",
                        "key": key,
                    },
                    timeout=8,
                )
                r.raise_for_status()
                rows = r.json()["rows"]
                for origin, row in zip(batch, rows):
                    el = row["elements"][0]
                    if el.get("status") == "OK":
                        minutes.append(round(el["duration"]["value"] / 60))
                    else:
                        minutes.append(estimate_minutes(origin, dest, mode))
            return minutes, False
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            log.warning("Distance Matrix indisponible, estimation locale : %s", exc)
    return [estimate_minutes(o, dest, mode) for o in origins], True
