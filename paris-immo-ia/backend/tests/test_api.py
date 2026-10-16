from app.services.alerts import check_alerts

from .conftest import make_property

SPEC_QUERY = "Je cherche un truc calme mais proche de bars sympas, à moins de 30 min en métro de Châtelet, avec la fibre, 1300 € max"


def test_health(client):
    r = client.get("/api/health")
    assert r.json()["llm_provider"] == "heuristic"


def test_chat_completes_with_external_sources(client, db, landlord):
    make_property(db, landlord)
    r = client.post("/api/chat", json={"messages": [{"role": "user", "content": SPEC_QUERY}]})
    body = r.json()
    assert r.status_code == 200
    assert body["ready_to_search"]
    assert len(body["matches"]) == 3
    assert body["matches"][0]["source"] == "local", "les biens de la base locale passent en priorité"
    assert body["used_external_sources"]
    assert all(m["why_for_you"] for m in body["matches"])
    assert all(m["rent_cc"] <= 1300 * 1.05 and "fibre" in m["features"] for m in body["matches"])


def test_chat_local_only_when_three_perfect_matches(client, db, landlord):
    for i in range(4):
        make_property(db, landlord, title=f"Bien {i}")
    r = client.post("/api/chat", json={"messages": [{"role": "user", "content": SPEC_QUERY}]})
    body = r.json()
    assert len(body["matches"]) == 3
    assert {m["source"] for m in body["matches"]} == {"local"}
    assert not body["used_external_sources"]


def test_unrealistic_commute_is_relaxed_with_note(client):
    r = client.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": "calme, à moins de 30 min en métro de Télécom Paris, avec la fibre"}]},
    )
    body = r.json()
    assert len(body["matches"]) == 3
    assert body["notes"] and "Télécom Paris" in body["notes"][0]


def test_chat_asks_follow_up_without_searching(client):
    r = client.post("/api/chat", json={"messages": [{"role": "user", "content": "Salut"}]})
    assert r.json()["matches"] == [] and not r.json()["ready_to_search"]


def test_transcribe_without_key_returns_503(client):
    r = client.post("/api/transcribe", files={"audio": ("a.webm", b"1234", "audio/webm")})
    assert r.status_code == 503


def test_alert_fires_once_for_new_90_percent_match(client, db, landlord, session_factory):
    chat = client.post("/api/chat", json={"messages": [{"role": "user", "content": SPEC_QUERY}]}).json()
    r = client.post(
        "/api/alerts", json={"email": "Locataire@Example.com", "query": SPEC_QUERY, "criteria": chat["criteria"]}
    )
    assert r.status_code == 201 and r.json()["email"] == "locataire@example.com"

    # Un bien qui ne colle pas (trop cher) et un bien parfait sont publiés après l'alerte.
    make_property(db, landlord, title="Trop cher", rent_hc=2000)
    make_property(db, landlord, title="Parfait", quartier="charonne", latitude=48.855, longitude=2.388)

    with session_factory() as s:
        sent = check_alerts(s)
    assert len(sent) == 1
    assert [m.candidate.title for m in sent[0].matches] == ["Parfait"]
    assert sent[0].matches[0].score > 90

    with session_factory() as s:
        assert check_alerts(s) == []
