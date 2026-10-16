"""Moteur de matching : filtres durs + score pondéré (0-100) explicable.

Priorité aux biens de notre base PostgreSQL ; si moins de `top_k` biens
atteignent le seuil "Perfect Match", on complète avec les sources externes
(simulées dans scraper_mock). Le résultat n'excède jamais `top_k` biens.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..knowledge.paris import Quartier, haversine_km, quartiers
from ..models import Property, PropertyStatus
from ..schemas import CommuteInfo, PropertyCard, ScoreBreakdown, SearchCriteria
from . import commute as commute_service

DPE_ORDER = "ABCDEFG"
DPE_SCORE = {"A": 1.0, "B": 0.9, "C": 0.8, "D": 0.65, "E": 0.45, "F": 0.25, "G": 0.0}

BUDGET_TOLERANCE = 1.05
COMMUTE_TOLERANCE = 1.25


@dataclass
class Candidate:
    id: str
    source: str
    title: str
    description: str
    address: str
    quartier: str
    arrondissement: int
    latitude: float
    longitude: float
    rent_hc: int
    charges: int
    surface: float
    rooms: int
    floor: int
    has_elevator: bool
    furnished: bool
    dpe: str
    features: set[str]
    photos: list[str] = field(default_factory=list)
    external_url: str | None = None
    created_at: datetime | None = None

    @property
    def rent_cc(self) -> int:
        return self.rent_hc + self.charges

    @classmethod
    def from_property(cls, p: Property) -> "Candidate":
        flags = {
            "fibre": p.has_fiber,
            "ascenseur": p.has_elevator,
            "balcon": p.has_balcony,
            "parking": p.has_parking,
            "cave": p.has_cellar,
            "lave_vaisselle": p.has_dishwasher,
            "animaux": p.pets_allowed,
            "sur_cour": p.faces_courtyard,
            "meuble": p.furnished,
        }
        return cls(
            id=str(p.id),
            source="local",
            title=p.title,
            description=p.description,
            address=p.address,
            quartier=p.quartier,
            arrondissement=p.arrondissement,
            latitude=p.latitude,
            longitude=p.longitude,
            rent_hc=p.rent_hc,
            charges=p.charges,
            surface=p.surface,
            rooms=p.rooms,
            floor=p.floor,
            has_elevator=p.has_elevator,
            furnished=p.furnished,
            dpe=p.dpe.value if hasattr(p.dpe, "value") else str(p.dpe),
            features={k for k, v in flags.items() if v},
            photos=list(p.photos or []),
            created_at=p.created_at,
        )


@dataclass
class Scored:
    candidate: Candidate
    score: int
    breakdown: list[ScoreBreakdown]
    commute: CommuteInfo | None


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


def ambiance_fit(q: Quartier, c: SearchCriteria, faces_courtyard: bool) -> tuple[float, str]:
    """Adéquation d'un micro-quartier (et de l'exposition du bien) avec l'ambiance voulue."""
    parts: list[tuple[float, str]] = []
    for tag in c.ambiance:
        if tag == "calme":
            base = q.calme / 10
            if faces_courtyard and base < 0.9:
                parts.append((0.9, "calme garanti côté cour"))
            else:
                parts.append((base, f"calme {q.calme}/10"))
        elif tag == "festif":
            parts.append((q.vie_nocturne / 10, f"vie nocturne {q.vie_nocturne}/10"))
        elif tag == "familial":
            parts.append((q.familial / 10, f"familial {q.familial}/10"))
        else:
            parts.append((1.0 if tag in q.tags else 0.3, f"{tag} {'✓' if tag in q.tags else '✗'}"))
    if c.nightlife_nearby:
        parts.append((_clamp(q.vie_nocturne / 7), f"bars à proximité {q.vie_nocturne}/10"))
    if not parts:
        return 1.0, ""
    return sum(s for s, _ in parts) / len(parts), ", ".join(d for _, d in parts)


def passes_hard_filters(
    cand: Candidate, c: SearchCriteria, commute_minutes: int | None, relax_commute: bool = False
) -> bool:
    if c.budget_max and cand.rent_cc > c.budget_max * BUDGET_TOLERANCE:
        return False
    if c.surface_min and cand.surface < c.surface_min * 0.9:
        return False
    if c.rooms_min and cand.rooms < c.rooms_min:
        return False
    if c.furnished is not None and cand.furnished != c.furnished:
        return False
    if any(f not in cand.features for f in c.must_have):
        return False
    if c.dpe_max and DPE_ORDER.index(cand.dpe) > DPE_ORDER.index(c.dpe_max):
        return False
    if c.floor_min is not None and cand.floor < c.floor_min:
        return False
    if (
        not relax_commute
        and c.commute
        and commute_minutes is not None
        and commute_minutes > c.commute.max_minutes * COMMUTE_TOLERANCE
    ):
        return False
    return True


def score_candidate(cand: Candidate, c: SearchCriteria, commute: CommuteInfo | None) -> tuple[int, list[ScoreBreakdown]]:
    q = quartiers().get(cand.quartier)
    items: list[ScoreBreakdown] = []

    def add(label: str, score: float, weight: float, detail: str) -> None:
        items.append(ScoreBreakdown(label=label, score=round(_clamp(score), 3), weight=weight, detail=detail))

    if c.budget_max:
        over = cand.rent_cc - c.budget_max
        s = 1.0 if over <= 0 else 1 - over / (c.budget_max * (BUDGET_TOLERANCE - 1))
        detail = f"{cand.rent_cc} € CC / {c.budget_max} €" + (" (dans le budget)" if over <= 0 else f" (+{over} €)")
        add("Budget", s, 20, detail)

    if c.commute and commute:
        limit = c.commute.max_minutes
        s = 1.0 if commute.minutes <= limit else 1 - (commute.minutes - limit) / (limit * (COMMUTE_TOLERANCE - 1))
        approx = "≈ " if commute.estimated else ""
        add("Trajet", s, 25, f"{approx}{commute.minutes} min vers {commute.destination} (max {limit})")

    if c.quartiers or c.arrondissements:
        if cand.quartier in c.quartiers:
            s, detail = 1.0, "dans le quartier demandé"
        elif cand.arrondissement in c.arrondissements:
            s, detail = 0.9, f"dans le {cand.arrondissement}e demandé"
        else:
            dists = [
                haversine_km(cand.latitude, cand.longitude, quartiers()[slug].lat, quartiers()[slug].lng)
                for slug in c.quartiers
                if slug in quartiers()
            ]
            nearest = min(dists) if dists else 5.0
            s, detail = _clamp(1 - nearest / 3), f"à {nearest:.1f} km du quartier demandé"
        add("Localisation", s, 20, detail)
    elif c.suggested_quartiers:
        inside = cand.quartier in c.suggested_quartiers
        add("Quartier suggéré", 1.0 if inside else 0.5, 10, "quartier recommandé" if inside else "hors suggestions")

    if q and (c.ambiance or c.nightlife_nearby):
        s, detail = ambiance_fit(q, c, "sur_cour" in cand.features)
        add("Ambiance", s, 20, f"{q.nom} : {detail}")

    if c.surface_min or c.rooms_min:
        ok_surface = not c.surface_min or cand.surface >= c.surface_min
        ok_rooms = not c.rooms_min or cand.rooms >= c.rooms_min
        add("Surface", 1.0 if ok_surface and ok_rooms else 0.6, 10, f"{cand.surface:g} m², {cand.rooms} pièce(s)")

    if c.must_have:
        add("Indispensables", 1.0, 5, ", ".join(c.must_have) + " ✓")

    if c.nice_to_have:
        present = [f for f in c.nice_to_have if f in cand.features]
        add("Bonus", len(present) / len(c.nice_to_have), 10, ", ".join(present) or "aucun bonus")

    add("Énergie", DPE_SCORE.get(cand.dpe, 0.5), 5, f"DPE {cand.dpe}")

    total_w = sum(i.weight for i in items)
    score = round(100 * sum(i.score * i.weight for i in items) / total_w)
    return score, items


def rank(candidates: list[Candidate], c: SearchCriteria, relax_commute: bool = False) -> list[Scored]:
    commutes: list[CommuteInfo | None] = [None] * len(candidates)
    if c.commute and candidates:
        dest = commute_service.resolve_destination(c.commute.destination)
        if dest:
            minutes, estimated = commute_service.travel_minutes(
                [(x.latitude, x.longitude) for x in candidates], dest, c.commute.mode
            )
            commutes = [
                CommuteInfo(destination=dest.label, minutes=m, mode=c.commute.mode, estimated=estimated)
                for m in minutes
            ]
    scored = []
    for cand, info in zip(candidates, commutes):
        if not passes_hard_filters(cand, c, info.minutes if info else None, relax_commute):
            continue
        score, breakdown = score_candidate(cand, c, info)
        scored.append(Scored(cand, score, breakdown, info))
    scored.sort(key=lambda s: (s.score, s.candidate.created_at or datetime.min), reverse=True)
    return scored


def load_local_candidates(db: Session, c: SearchCriteria, limit: int = 500) -> list[Candidate]:
    stmt = select(Property).where(Property.status == PropertyStatus.ACTIVE)
    # Pré-filtrage SQL des critères durs simples ; le reste est évalué en Python.
    if c.budget_max:
        stmt = stmt.where(Property.rent_hc + Property.charges <= c.budget_max * BUDGET_TOLERANCE)
    if c.surface_min:
        stmt = stmt.where(Property.surface >= c.surface_min * 0.9)
    if c.rooms_min:
        stmt = stmt.where(Property.rooms >= c.rooms_min)
    if c.furnished is not None:
        stmt = stmt.where(Property.furnished == c.furnished)
    stmt = stmt.order_by(Property.created_at.desc()).limit(limit)
    return [Candidate.from_property(p) for p in db.scalars(stmt)]


def _diversify(
    scored: list[Scored], n: int, key: Callable[[Scored], float] = lambda s: s.score, penalty: int = 6
) -> list[Scored]:
    """Sélection gloutonne qui pénalise les doublons de quartier pour varier le Top 3."""
    pool, picked, seen = list(scored), [], {}
    while pool and len(picked) < n:
        best = max(pool, key=lambda s: key(s) - penalty * seen.get(s.candidate.quartier, 0))
        pool.remove(best)
        picked.append(best)
        seen[best.candidate.quartier] = seen.get(best.candidate.quartier, 0) + 1
    return picked


@dataclass
class MatchResult:
    matches: list[Scored]
    used_external: bool
    notes: list[str] = field(default_factory=list)


def find_matches(db: Session, c: SearchCriteria) -> MatchResult:
    from . import scraper_mock

    settings = get_settings()
    k, threshold = settings.top_k, settings.perfect_match_score

    local_candidates = load_local_candidates(db, c)
    local = rank(local_candidates, c)
    perfect = _diversify([s for s in local if s.score >= threshold], k)
    if len(perfect) >= k:
        return MatchResult(perfect, used_external=False)

    external_candidates = scraper_mock.search_external(c)
    chosen = {s.candidate.id for s in perfect}
    rest = sorted(
        [s for s in local + rank(external_candidates, c) if s.candidate.id not in chosen],
        key=lambda s: s.score,
        reverse=True,
    )
    final = perfect + _diversify(rest, k - len(perfect))

    notes: list[str] = []
    if len(final) < k and c.commute:
        # Trajet irréaliste (ex. 30 min de Palaiseau depuis Paris) : on propose les biens
        # les plus proches plutôt qu'une page vide, en le signalant clairement.
        chosen = {s.candidate.id for s in final}
        relaxed = [
            s
            for s in rank(local_candidates + external_candidates, c, relax_commute=True)
            if s.candidate.id not in chosen
        ]
        # Le trajet devient le critère principal (2 points par minute), le score départage.
        final += _diversify(relaxed, k - len(final), key=lambda s: s.score - 2 * (s.commute.minutes if s.commute else 999))
        if relaxed:
            best = min(s.commute.minutes for s in final if s.commute)
            notes.append(
                f"Aucun logement à Paris ne respecte {c.commute.max_minutes} min vers {c.commute.destination} : "
                f"voici les plus proches (meilleur trajet ≈ {best} min)."
            )
    return MatchResult(final, used_external=any(s.candidate.source != "local" for s in final), notes=notes)


def to_card(s: Scored) -> PropertyCard:
    cand = s.candidate
    q = quartiers().get(cand.quartier)
    return PropertyCard(
        id=cand.id,
        source=cand.source,  # type: ignore[arg-type]
        external_url=cand.external_url,
        title=cand.title,
        description=cand.description,
        address=cand.address,
        quartier=cand.quartier,
        quartier_nom=q.nom if q else cand.quartier,
        arrondissement=cand.arrondissement,
        latitude=cand.latitude,
        longitude=cand.longitude,
        rent_cc=cand.rent_cc,
        rent_hc=cand.rent_hc,
        charges=cand.charges,
        surface=cand.surface,
        rooms=cand.rooms,
        floor=cand.floor,
        has_elevator=cand.has_elevator,
        furnished=cand.furnished,
        dpe=cand.dpe,  # type: ignore[arg-type]
        features=sorted(cand.features),  # type: ignore[arg-type]
        photos=cand.photos,
        match_score=s.score,
        breakdown=s.breakdown,
        commute=s.commute,
    )
