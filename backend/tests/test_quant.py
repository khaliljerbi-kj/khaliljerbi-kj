import numpy as np
import pytest

from app.quant import gbm, history, price_field


def test_gbm_shape_and_start():
    paths = gbm.simulate_gbm(10_000, 0.02, 0.05, years=10, steps_per_year=12, n_paths=101,
                             rng=np.random.default_rng(1))
    assert paths.shape == (101, 121)
    assert np.all(paths[:, 0] == 10_000)
    assert np.all(paths > 0)


def test_gbm_moments_match_theory():
    s0, mu, sigma, T = 10_000.0, 0.03, 0.08, 5.0
    paths = gbm.simulate_gbm(s0, mu, sigma, years=T, steps_per_year=4, n_paths=40_000,
                             rng=np.random.default_rng(7))
    terminal = paths[:, -1]
    # E[S_T] = S0 e^{mu T};  median = S0 e^{(mu - sigma²/2) T}
    assert terminal.mean() == pytest.approx(s0 * np.exp(mu * T), rel=0.01)
    assert np.median(terminal) == pytest.approx(s0 * np.exp((mu - sigma**2 / 2) * T), rel=0.01)
    log_ret = np.log(terminal / s0)
    assert log_ret.std() == pytest.approx(sigma * np.sqrt(T), rel=0.02)


def test_prob_loss_and_var():
    assert gbm.prob_loss(0.0, 0.1, 1.0) > 0.5  # Zero drift => median below S0.
    assert gbm.prob_loss(0.10, 0.05, 10.0) < 0.001
    assert 0.0 < gbm.value_at_risk(0.02, 0.05, 1.0) < 0.1


def test_scenarios_are_ordered():
    proj = gbm.project(10_000, 0.01, 0.04, seed=3)
    for h in proj["horizons"]:
        assert h["pessimistic"] < h["median"] < h["optimistic"]
    last = proj["points"][-1]
    assert last["p5"] < last["p25"] < last["median"] < last["p75"] < last["p95"]
    assert len(proj["points"]) == 41  # Quarterly over 10 years.


def test_price_field_bounds():
    lats = np.linspace(48.80, 48.92, 50)
    lons = np.linspace(2.20, 2.50, 50)
    grid = price_field.base_price_field(*np.meshgrid(lats, lons))
    assert grid.min() >= price_field.PRICE_MIN
    assert grid.max() <= price_field.PRICE_MAX
    # Saint-Germain-des-Prés should be pricier than Belleville.
    assert price_field.estimate_price(48.853, 2.333) > price_field.estimate_price(48.872, 2.383)


def test_street_lookup_is_stable():
    assert price_field.street_location("Rue de Rivoli") == price_field.KNOWN_STREETS["rue de rivoli"]
    assert price_field.street_location("Rue Inconnue") == price_field.street_location("rue  inconnue")
    assert price_field.normalize_street("Avenue des Champs-Élysées") == "avenue des champs-elysees"


def test_history_ends_at_current_price():
    df = history.build_history(11_000, seed=5)
    assert len(df) == 21
    assert df["price"].iloc[-1] == 11_000
    mu, sigma = history.calibrate(df)
    assert -0.2 < mu < 0.2 and 0 < sigma < 0.2
