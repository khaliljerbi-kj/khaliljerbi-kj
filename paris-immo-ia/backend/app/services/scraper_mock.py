"""Simulation d'un appel aux portails externes (SeLoger / Leboncoin).

En production ce module serait remplacé par un connecteur (API partenaire ou
flux XML). Les annonces sont générées de façon déterministe à partir des
critères pour que les résultats restent stables d'une requête à l'autre.
"""

import hashlib
import random

from ..knowledge.paris import quartiers
from ..schemas import SearchCriteria
from .matching import Candidate, ambiance_fit

ROOM_LABEL = {1: "Studio", 2: "2 pièces", 3: "3 pièces", 4: "4 pièces"}
DPES = "BCCDDDE"
EXTRA_FEATURES = ["fibre", "ascenseur", "balcon", "cave", "lave_vaisselle", "sur_cour", "animaux"]


def _target_quartiers(c: SearchCriteria) -> list[str]:
    explicit = [s for s in c.quartiers if s in quartiers()]
    if explicit:
        return explicit
    suggested = [s for s in c.suggested_quartiers if s in quartiers()]
    if suggested:
        return suggested
    if c.arrondissements:
        by_arr = [q.slug for q in quartiers().values() if q.arrondissement in c.arrondissements]
        if by_arr:
            return by_arr
    ranked = sorted(quartiers().values(), key=lambda q: ambiance_fit(q, c, False)[0], reverse=True)
    return [q.slug for q in ranked[:6]]


def search_external(c: SearchCriteria, n: int = 12) -> list[Candidate]:
    seed = int(hashlib.sha256(c.model_dump_json().encode()).hexdigest()[:12], 16)
    rng = random.Random(seed)
    targets = _target_quartiers(c)
    results = []
    for i in range(n):
        q = quartiers()[targets[i % len(targets)]]
        rooms = max(c.rooms_min or 1, rng.choice([1, 1, 2, 2, 3]))
        furnished = c.furnished if c.furnished is not None else rng.random() < 0.5
        per_m2 = rng.uniform(28, 38) + (3 if furnished else 0)
        base_surface = {1: rng.uniform(18, 30), 2: rng.uniform(32, 48), 3: rng.uniform(50, 68)}.get(rooms, 80)
        surface = round(max(base_surface, c.surface_min or 0) + rng.uniform(0, 4))
        rent_cc = round(surface * per_m2 / 10) * 10
        if c.budget_max:
            # Les portails filtrent déjà côté serveur : on reste autour du budget.
            rent_cc = min(rent_cc, round(c.budget_max * rng.uniform(0.85, 1.03)))
        charges = round(rent_cc * 0.08 / 5) * 5
        features = set(c.must_have) | {f for f in EXTRA_FEATURES if rng.random() < 0.35}
        if furnished:
            features.add("meuble")
        else:
            features.discard("meuble")
        floor = rng.randint(0, 6)
        portal = "seloger" if i % 2 == 0 else "leboncoin"
        lat = q.lat + rng.uniform(-0.004, 0.004)
        lng = q.lng + rng.uniform(-0.005, 0.005)
        title = f"{ROOM_LABEL.get(rooms, f'{rooms} pièces')} {'meublé' if furnished else 'vide'} {surface} m² – {q.nom}"
        results.append(
            Candidate(
                id=f"{portal}-{seed % 100000:05d}-{i}",
                source=portal,
                title=title,
                description=(
                    f"Annonce {portal.capitalize()} (simulée). {ROOM_LABEL.get(rooms, '')} de {surface} m² au "
                    f"{floor}e étage, quartier {q.nom}. {q.description}"
                ),
                # Les portails masquent l'adresse exacte avant la prise de contact.
                address=f"Secteur {q.nom}, 750{q.arrondissement:02d} Paris",
                quartier=q.slug,
                arrondissement=q.arrondissement,
                latitude=round(lat, 5),
                longitude=round(lng, 5),
                rent_hc=rent_cc - charges,
                charges=charges,
                surface=surface,
                rooms=rooms,
                floor=floor,
                has_elevator="ascenseur" in features,
                furnished=furnished,
                dpe=rng.choice([d for d in DPES if not c.dpe_max or d <= c.dpe_max] or [c.dpe_max]),
                features=features,
                external_url=None,
            )
        )
    return results
