"""Base de connaissances parisienne partagée (shared/*.json)."""

import json
import re
import math
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

SHARED_DIR = Path(__file__).resolve().parents[3] / "shared"


@dataclass(frozen=True)
class Quartier:
    slug: str
    nom: str
    arrondissement: int
    lat: float
    lng: float
    calme: int
    vie_nocturne: int
    familial: int
    tags: tuple[str, ...]
    lignes: tuple[str, ...]
    description: str
    aliases: tuple[str, ...]


@dataclass(frozen=True)
class Place:
    slug: str
    nom: str
    aliases: tuple[str, ...]
    lat: float
    lng: float


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in text if not unicodedata.combining(c))


@lru_cache
def quartiers() -> dict[str, Quartier]:
    raw = json.loads((SHARED_DIR / "quartiers.json").read_text(encoding="utf-8"))["quartiers"]
    return {
        q["slug"]: Quartier(
            **{**q, "tags": tuple(q["tags"]), "lignes": tuple(q["lignes"]), "aliases": tuple(q["aliases"])}
        ) for q in raw
    }


@lru_cache
def places() -> list[Place]:
    raw = json.loads((SHARED_DIR / "places.json").read_text(encoding="utf-8"))["places"]
    return [Place(**{**p, "aliases": tuple(p["aliases"])}) for p in raw]


def find_place(query: str) -> Place | None:
    """Résout une destination connue ('Télécom Paris', 'la Défense'…) sans API externe."""
    q = normalize(query).strip()
    best: tuple[int, Place] | None = None
    for place in places():
        for alias in (place.nom, *place.aliases):
            a = normalize(alias)
            if re.search(rf"(?<![\w']){re.escape(a)}(?![\w'])", q) or (len(q) >= 4 and q in a):
                if best is None or len(a) > best[0]:
                    best = (len(a), place)
    return best[1] if best else None


def find_quartiers_in_text(text: str) -> list[str]:
    t = normalize(text)
    found = []
    for q in quartiers().values():
        names = {normalize(q.nom), normalize(q.slug.replace("-", " ")), *(normalize(a) for a in q.aliases)}
        if any(re.search(rf"\b{re.escape(n)}\b", t) for n in names):
            found.append(q.slug)
    return found


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def quartiers_prompt_digest() -> str:
    """Résumé compact injecté dans le prompt système du LLM."""
    lines = []
    for q in quartiers().values():
        lines.append(
            f"- {q.slug} ({q.nom}, {q.arrondissement}e) calme={q.calme} nuit={q.vie_nocturne} "
            f"famille={q.familial} tags={','.join(q.tags)} lignes={','.join(q.lignes)}"
        )
    return "\n".join(lines)
