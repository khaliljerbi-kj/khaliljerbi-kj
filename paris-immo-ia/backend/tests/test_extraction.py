from app.schemas import ChatMessage, SearchCriteria
from app.services.heuristic import heuristic_extract
from app.services.llm import _sanitize, extraction_tool_schema


def extract(text: str, previous: SearchCriteria | None = None):
    return heuristic_extract([ChatMessage(role="user", content=text)], previous)


def test_spec_example_sentence():
    r = extract(
        "Je cherche un truc calme mais proche de bars sympas, à moins de 30 min en métro de Télécom Paris, avec la fibre."
    )
    c = r.criteria
    assert c.commute and c.commute.destination.startswith("Télécom Paris")
    assert c.commute.max_minutes == 30 and c.commute.mode == "transit"
    assert c.ambiance == ["calme"]
    assert c.nightlife_nearby is True
    assert c.must_have == ["fibre"]
    assert c.budget_max is None
    assert c.suggested_quartiers, "le lifestyle doit déduire des micro-quartiers"
    assert r.ready_to_search and "budget" in r.missing


def test_micro_quartier_budget_and_type():
    c = extract("Studio meublé aux Batignolles ou à Montorgueil, 1 200 € max, idéalement un balcon").criteria
    assert c.quartiers == ["batignolles", "montorgueil"]
    assert c.knows_paris is True
    assert c.rooms_min == 1 and c.furnished is True
    assert c.budget_max == 1200
    assert c.nice_to_have == ["balcon"] and c.must_have == []


def test_follow_up_merges_with_previous_criteria():
    first = extract("Un T2 vers la Butte-aux-Cailles").criteria
    second = extract("budget 1,5k, au 2e étage minimum c'est pas grave", first).criteria
    assert second.rooms_min == 2
    assert second.quartiers == ["butte-aux-cailles"]
    assert second.budget_max == 1500
    assert second.arrondissements == []  # "2e étage" n'est pas un arrondissement


def test_lifestyle_for_newcomer():
    c = extract("Je ne connais pas Paris, je veux un quartier familial avec des parcs").criteria
    assert c.knows_paris is False
    assert {"familial", "verdoyant"} <= set(c.ambiance)
    assert "buttes-chaumont" in c.suggested_quartiers


def test_nothing_actionable_asks_question():
    r = extract("Bonjour !")
    assert not r.ready_to_search
    assert "?" in r.reply


def test_place_alias_needs_word_boundary():
    c = extract("un appart ensoleillé à 20 min de Station F").criteria
    assert c.commute and c.commute.destination == "Station F"


def test_llm_output_sanitized():
    raw = {
        "reply": "ok",
        "ready_to_search": True,
        "criteria": {"quartiers": ["batignolles", "atlantide"], "ambiance": ["calme"], "budget_max": 1300},
    }
    r = _sanitize(raw)
    assert r.criteria.quartiers == ["batignolles"]


def test_tool_schema_has_no_refs():
    schema = extraction_tool_schema()
    assert "$ref" not in str(schema) and "$defs" not in str(schema)
    assert schema["properties"]["criteria"]["properties"]["commute"]
