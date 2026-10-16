from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_estimate_by_coordinates():
    r = client.get("/api/estimate", params={"lat": 48.8566, "lon": 2.3522})
    assert r.status_code == 200
    body = r.json()
    assert 7_000 <= body["current_price_m2"] <= 15_000
    assert len(body["history"]) == 21
    assert body["history"][-1]["price"] == body["current_price_m2"]
    assert len(body["projection"]) == 41
    assert [h["years"] for h in body["horizons"]] == [1, 5, 10]
    assert {s["key"] for s in body["scenarios"]} == {"pessimistic", "median", "optimistic"}
    assert body["location"]["arrondissement"] in range(1, 21)


def test_estimate_is_deterministic():
    params = {"lat": 48.85, "lon": 2.33, "street": "Rue de Rennes"}
    assert client.get("/api/estimate", params=params).json() == client.get("/api/estimate", params=params).json()


def test_estimate_by_street_and_post():
    r = client.post("/api/estimate", json={"street": "Avenue Montaigne"})
    assert r.status_code == 200
    assert r.json()["location"]["label"] == "Avenue Montaigne"


def test_estimate_validation():
    assert client.get("/api/estimate").status_code == 422
    assert client.get("/api/estimate", params={"lat": 48.85}).status_code == 422
    assert client.get("/api/estimate", params={"lat": 45.76, "lon": 4.83}).status_code == 422  # Lyon


def test_price_grid():
    body = client.get("/api/price-grid").json()
    assert len(body["values"]) == body["n_lat"] * body["n_lon"]
    assert min(body["values"]) >= 7_000 and max(body["values"]) <= 15_000
