"""Gabarit de secours pour l'encadré « Pourquoi ce bien est fait pour vous ? »."""

from ..knowledge.paris import quartiers
from ..schemas import PropertyCard, SearchCriteria


def template_pitch(c: SearchCriteria, card: PropertyCard) -> str:
    q = quartiers().get(card.quartier)
    sentences: list[str] = []
    courtyard = "sur_cour" in card.features

    if q and "calme" in c.ambiance and courtyard and q.calme < 7:
        sentences.append(
            f"Bien que {q.nom} soit un quartier animé, ce logement donne sur cour, ce qui respecte votre besoin de calme."
        )
    elif q and "calme" in c.ambiance and q.calme >= 7:
        sentences.append(f"{q.nom} est l'un des secteurs les plus paisibles de Paris ({q.calme}/10 en calme).")
    elif q:
        sentences.append(f"Situé à {q.nom} ({card.arrondissement}e) : {q.description[0].lower()}{q.description[1:]}")

    if q and "familial" in c.ambiance and q.familial >= 7:
        sentences.append(f"Le quartier est très prisé des familles ({q.familial}/10) : écoles, squares et commerces de proximité.")
    if q and c.nightlife_nearby and q.vie_nocturne >= 6:
        sentences.append("Vous aurez des bars et restaurants sympas à quelques minutes à pied.")

    if card.commute:
        lignes = ""
        if q and q.lignes:
            lignes = f" ({'lignes' if len(q.lignes) > 1 else 'ligne'} {', '.join(q.lignes)})"
        approx = "environ " if card.commute.estimated else ""
        sentences.append(f"Comptez {approx}{card.commute.minutes} min jusqu'à {card.commute.destination}{lignes}.")

    if c.budget_max:
        delta = c.budget_max - card.rent_cc
        if delta >= 0:
            sentences.append(f"À {card.rent_cc} € CC, il vous laisse {delta} € de marge sur votre budget.")
        else:
            sentences.append(f"Il dépasse votre budget de {-delta} €, compensé par ses autres atouts.")

    met = [f for f in c.must_have if f in card.features]
    if met:
        sentences.append("Vos indispensables sont cochés : " + ", ".join(f.replace("_", " ") for f in met) + ".")
    return " ".join(sentences)
