from dataclasses import replace

import numpy as np
import pytest

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

    
@pytest.mark.parametrize("capacity", [0, -5, 30.5, True])
def test_invalid_capacity(capacity):
    with pytest.raises(ValueError) as error:
        Params(capacity=capacity)

    assert str(error.value) == (
        f"capacity must be a positive integer, got {capacity!r}"
    )


@pytest.mark.parametrize("capacity", [100, np.int64(100)])
def test_valid_capacity(capacity):
    params = Params(capacity=capacity)

    assert params.capacity == 100
    assert params.booking_limit == 110

@pytest.mark.parametrize(
    "overbooking_level",
    [-1.1, float("nan"), float("inf"), -float("inf")],
)
def test_invalid_overbooking_level(overbooking_level):
    with pytest.raises(ValueError, match="overbooking_level"):
        Params(overbooking_level=overbooking_level)


@pytest.mark.parametrize("overbooking_level", [-1, 0, 0.2])
def test_valid_overbooking_level(overbooking_level):
    params = Params(overbooking_level=overbooking_level)
    assert params.overbooking_level == overbooking_level


@pytest.mark.parametrize(
    "shock_cv",
    [-0.1, float("nan"), float("inf"), -float("inf")],
)
def test_invalid_shock_cv(shock_cv):
    with pytest.raises(ValueError, match="shock_cv"):
        Params(shock_cv=shock_cv)


@pytest.mark.parametrize("shock_cv", [0, 0.5])
def test_valid_shock_cv(shock_cv):
    params = Params(shock_cv=shock_cv)
    assert params.shock_cv == shock_cv


@pytest.mark.parametrize(
    "n_days",
    [0, -1, 2.5, True, float("nan"), float("inf")],
)
def test_invalid_n_days(n_days):
    with pytest.raises(ValueError, match="n_days"):
        Params(n_days=n_days)


@pytest.mark.parametrize("n_days", [1, np.int64(10)])
def test_valid_n_days(n_days):
    params = Params(n_days=n_days)
    assert params.n_days == n_days


@pytest.mark.parametrize(
    "share",
    [-0.1, float("nan"), float("inf"), -float("inf")],
)
def test_invalid_segment_share(share):
    segment = replace(Params().segments[0], share=share)

    with pytest.raises(ValueError, match="share"):
        Params(segments=(segment,))


def test_empty_segments():
    with pytest.raises(ValueError, match="segments"):
        Params(segments=())


def test_zero_total_segment_share():
    segment = replace(Params().segments[0], share=0)

    with pytest.raises(ValueError, match="shares"):
        Params(segments=(segment,))


def test_valid_unnormalised_segment_shares():
    original = Params().segments[0]
    segments = (
        replace(original, share=0),
        replace(original, share=2),
        replace(original, share=3),
    )

    params = Params(segments=segments)

    assert sum(segment.share for segment in params.segments) == 5