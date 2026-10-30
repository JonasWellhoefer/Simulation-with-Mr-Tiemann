from dataclasses import replace

import numpy as np

from hotel_sim import Params, run_replications, simulate
from hotel_sim import analytic


def test_reproducible():
    p = Params(n_days=40)
    a, b = simulate(p, seed=3), simulate(p, seed=3)
    assert np.array_equal(a.profit, b.profit)


def test_matches_binomial_baseline():
    """Model reduces to Binomial(N, p) in the degenerate case."""
    p = Params.binomial_baseline(bookings=109, show_prob=0.9, n_days=1500)
    assert p.booking_limit == 109
    res = run_replications(p, n_runs=6, seed=1)
    assert abs(res["p_denied"]["mean"] - analytic.prob_denied(100, 109, 0.9)) < 0.03
    exact = analytic.expected_profit(100, 109, 0.9, 120.0, 250.0)
    lo, hi = res["mean_profit"]["ci95"]
    assert lo - 25 < exact < hi + 25


def test_no_overbooking_never_denies():
    p = Params(overbooking_level=0.0, walkin_rate=0.0, n_days=60)
    assert simulate(p, seed=0).denied.sum() == 0


def test_capacity_never_exceeded():
    p = Params(overbooking_level=0.3, n_days=60)
    assert simulate(p, seed=0).occupied.max() <= p.capacity


def test_shared_shock_increases_risk():
    """Correlated no-shows: same mean, heavier tail -> more denied guests."""
    base = Params(overbooking_level=0.12, n_days=120)
    plain = run_replications(base, n_runs=12, seed=5)
    shocked = run_replications(replace(base, shock_cv=0.5), n_runs=12, seed=5)
    assert shocked["mean_denied"]["mean"] > plain["mean_denied"]["mean"]
    assert shocked["cvar_5"] < plain["cvar_5"]
