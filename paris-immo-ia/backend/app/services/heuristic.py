"""Extracteur à base de règles : utilisé sans clé LLM (dev, tests) et en secours si le LLM échoue."""

import re

from ..knowledge.paris import find_place, find_quartiers_in_text, normalize, quartiers
from ..schemas import ChatMessage, Commute, ExtractionResult, SearchCriteria

AMBIANCE_PATTERNS: dict[str, str] = {
    "calme": r"\b(calme|tranquille|silencieux|au calme|paisible)\b",
    "festif": r"\b(festif|fetard|faire la fete|vie nocturne|soirees?)\b",
    "familial": r"\b(familial|famille|enfants?|bebe|creche)\b",
    "branche": r"\b(branche|bobo|hipster|tendance)\b",
    "etudiant": r"\b(etudiant|etudiante|etudiants)\b",
    "chic": r"\b(chic|bourgeois|standing|haut de gamme)\b",
    "authentique": r"\b(authentique|village|charme|populaire)\b",
    "verdoyant": r"\b(verdoyant|parcs?|nature|espaces? verts?|arbres)\b",
}

FEATURE_PATTERNS: dict[str, str] = {
    "fibre": r"\bfibre\b",
    "ascenseur": r"\bascenseur\b",
    "balcon": r"\b(balcon|terrasse|exterieur)\b",
    "parking": r"\b(parking|place de stationnement|garage)\b",
    "cave": r"\bcave\b",
    "lave_vaisselle": r"\blave[- ]vaisselle\b",
    "animaux": r"\b(chat|chien|animal|animaux)\b",
    "sur_cour": r"\bsur (la )?cour\b",
}
NICE_TO_HAVE = r"(ideal(ement)?|si possible|bonus|serait un plus|pas oblige)"


def _parse_budget(t: str) -> int | None:
    k = re.search(r"\b(\d{1,2})[,.]?(\d)?\s?k\b", t)
    if k:
        return int(k.group(1)) * 1000 + int(k.group(2) or 0) * 100
    candidates = re.findall(r"(\d[\d .]{2,6})\s*(?:€|euros?|eur\b|e/mois|e par mois|par mois|/mois)", t)
    candidates += re.findall(r"(?:budget|max(?:imum)?|moins de|jusqu'a)\s*(?:de\s*)?(\d[\d .]{2,6})(?!\s*(?:min|m2|m²|metres))", t)
    for raw in candidates:
        value = int(re.sub(r"[ .]", "", raw))
        if 300 <= value <= 20000:
            return value
    return None


def _parse_rooms(t: str) -> int | None:
    if re.search(r"\bstudio\b", t):
        return 1
    if m := re.search(r"\b[tf]([1-6])\b", t):
        return int(m.group(1))
    if m := re.search(r"\b([1-6])\s*pieces?\b", t):
        return int(m.group(1))
    if m := re.search(r"\b([1-5])\s*chambres?\b", t):
        return int(m.group(1)) + 1
    return None


def _parse_commute(t: str) -> Commute | None:
    m = re.search(r"(\d{1,3})\s*(?:min\b|mn\b|minutes?)", t)
    place = find_place(t)
    if not m or not place:
        return None
    mode = "transit"
    if re.search(r"\ba pied\b|\bmarche\b", t):
        mode = "walking"
    elif re.search(r"\bvelo\b", t):
        mode = "bicycling"
    return Commute(destination=place.nom, max_minutes=max(5, min(180, int(m.group(1)))), mode=mode)


def suggest_quartiers(criteria: SearchCriteria, limit: int = 4) -> list[str]:
    """Déduit des micro-quartiers du lifestyle (et du trajet) quand l'utilisateur n'en cite pas."""
    from .commute import estimate_minutes, resolve_destination  # imports locaux : évite un cycle
    from .matching import ambiance_fit

    dest = resolve_destination(criteria.commute.destination) if criteria.commute else None
    if not criteria.ambiance and not criteria.nightlife_nearby and not dest:
        return []

    def fit(q) -> float:
        # Le lifestyle prime : le trajet départage des quartiers d'ambiance comparable.
        score = 2 * ambiance_fit(q, criteria, faces_courtyard=False)[0]
        if dest and criteria.commute:
            minutes = estimate_minutes((q.lat, q.lng), dest, criteria.commute.mode)
            score += max(0.0, 1 - max(0, minutes - criteria.commute.max_minutes) / criteria.commute.max_minutes)
        return score

    return [q.slug for q in sorted(quartiers().values(), key=fit, reverse=True)[:limit]]


def _merge_unique(a: list, b: list) -> list:
    return list(dict.fromkeys([*a, *b]))


def heuristic_extract(messages: list[ChatMessage], previous: SearchCriteria | None) -> ExtractionResult:
    last = normalize(next(m.content for m in reversed(messages) if m.role == "user"))
    c = (previous or SearchCriteria()).model_copy(deep=True)

    if (budget := _parse_budget(last)) is not None:
        c.budget_max = budget
    if m := re.search(r"(\d{2,3})\s*(?:m2|m²|metres? carres)", last):
        c.surface_min = float(m.group(1))
    if (rooms := _parse_rooms(last)) is not None:
        c.rooms_min = rooms
    if re.search(r"\b(non[- ]meuble|vide)\b", last):
        c.furnished = False
    elif re.search(r"\bmeuble\b", last):
        c.furnished = True
    if commute := _parse_commute(last):
        c.commute = commute

    for tag, pattern in AMBIANCE_PATTERNS.items():
        if re.search(pattern, last) and tag not in c.ambiance:
            c.ambiance.append(tag)  # type: ignore[arg-type]
    if re.search(r"\b(bars?|restos?|restaurants?|sortir|terrasses?)\b", last):
        c.nightlife_nearby = True

    optional = re.search(NICE_TO_HAVE, last)
    for feature, pattern in FEATURE_PATTERNS.items():
        if re.search(pattern, last):
            target = c.nice_to_have if optional else c.must_have
            if feature not in c.must_have and feature not in c.nice_to_have:
                target.append(feature)  # type: ignore[arg-type]

    if m := re.search(r"\bdpe\s*(?:max(?:imum)?\s*)?([a-g])\b", last):
        c.dpe_max = m.group(1).upper()  # type: ignore[assignment]

    arrs = [
        int(n)
        for n, _ in re.findall(r"\b(\d{1,2})\s?(e|eme|er)\b(?!\s*etage)", last)
        if 1 <= int(n) <= 20
    ]
    arrs += [int(n) for n in re.findall(r"\b750(\d{2})\b", last) if 1 <= int(n) <= 20]
    c.arrondissements = _merge_unique(c.arrondissements, arrs)

    named = find_quartiers_in_text(last)
    if named:
        c.quartiers = _merge_unique(c.quartiers, named)
        c.knows_paris = True
    elif re.search(r"(connais pas (bien )?paris|nouveau a paris|nouvelle a paris|arrive a paris|jamais vecu a paris)", last):
        c.knows_paris = False
    if not c.quartiers:
        c.suggested_quartiers = suggest_quartiers(c)

    c.summary = summarize(c)
    missing = [label for label, value in (("budget", c.budget_max), ("surface", c.surface_min or c.rooms_min)) if not value]
    ready = c.is_searchable()
    return ExtractionResult(reply=_reply(c, ready, missing), criteria=c, ready_to_search=ready, missing=missing)


def summarize(c: SearchCriteria) -> str:
    parts = []
    if c.rooms_min:
        parts.append("studio" if c.rooms_min == 1 else f"{c.rooms_min} pièces min.")
    if c.surface_min:
        parts.append(f"{c.surface_min:g} m² min.")
    if c.budget_max:
        parts.append(f"≤ {c.budget_max} € CC")
    if c.furnished is not None:
        parts.append("meublé" if c.furnished else "vide")
    if c.commute:
        parts.append(f"≤ {c.commute.max_minutes} min de {c.commute.destination}")
    if c.ambiance:
        parts.append("ambiance " + ", ".join(c.ambiance))
    if c.nightlife_nearby:
        parts.append("bars à proximité")
    if c.must_have:
        parts.append("indispensable : " + ", ".join(c.must_have))
    if c.quartiers:
        parts.append("quartiers : " + ", ".join(quartiers()[s].nom for s in c.quartiers if s in quartiers()))
    return " · ".join(parts)


def _reply(c: SearchCriteria, ready: bool, missing: list[str]) -> str:
    if not ready:
        return (
            "Dites-m'en un peu plus : votre budget charges comprises, le lieu où vous vous rendez chaque jour "
            "ou l'ambiance de quartier que vous recherchez ?"
        )
    text = f"C'est noté : {c.summary}."
    if not c.quartiers and c.suggested_quartiers:
        noms = ", ".join(quartiers()[s].nom for s in c.suggested_quartiers)
        text += f" D'après votre style de vie, je cible notamment : {noms}."
    text += " Voici mes 3 meilleures correspondances."
    if "budget" in missing:
        text += " Quel est votre budget maximum charges comprises ?"
    return text
