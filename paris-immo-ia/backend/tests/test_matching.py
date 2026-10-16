from app.schemas import Commute, SearchCriteria
from app.services.matching import Candidate, rank
from app.services.scraper_mock import search_external


def cand(**kw) -> Candidate:
    base = dict(
        id="x", source="local", title="t", description="d", address="a", quartier="oberkampf",
        arrondissement=11, latitude=48.865, longitude=2.378, rent_hc=1100, charges=100, surface=35,
        rooms=2, floor=2, has_elevator=False, furnished=False, dpe="C", features={"fibre"},
    )
    base.update(kw)
    return Candidate(**base)


def test_courtyard_satisfies_calm_in_lively_area():
    c = SearchCriteria(ambiance=["calme"], nightlife_nearby=True)
    street = cand(id="rue")
    court = cand(id="cour", features={"fibre", "sur_cour"})
    ranked = rank([street, court], c)
    assert [s.candidate.id for s in ranked] == ["cour", "rue"]


def test_hard_filters():
    c = SearchCriteria(budget_max=1000, must_have=["fibre"], furnished=False)
    ok = cand(id="ok", rent_hc=900, charges=50)
    too_expensive = cand(id="cher", rent_hc=1200)
    no_fiber = cand(id="sans-fibre", rent_hc=900, charges=50, features=set())
    furnished = cand(id="meuble", rent_hc=900, charges=50, furnished=True)
    assert [s.candidate.id for s in rank([ok, too_expensive, no_fiber, furnished], c)] == ["ok"]


def test_commute_scoring_prefers_closer():
    c = SearchCriteria(commute=Commute(destination="Châtelet", max_minutes=20))
    near = cand(id="near", quartier="marais", latitude=48.859, longitude=2.36)
    far = cand(id="far", quartier="auteuil", latitude=48.848, longitude=2.265)
    ranked = rank([far, near], c)
    assert ranked[0].candidate.id == "near"
    assert ranked[0].commute and ranked[0].commute.estimated


def test_mock_scraper_is_deterministic_and_respects_hard_criteria():
    c = SearchCriteria(budget_max=1400, quartiers=["batignolles"], must_have=["fibre"], dpe_max="D")
    a, b = search_external(c), search_external(c)
    assert [x.id for x in a] == [x.id for x in b]
    assert all(x.quartier == "batignolles" and "fibre" in x.features and x.dpe <= "D" for x in a)
    assert all(x.rent_cc <= 1400 * 1.05 for x in a)
