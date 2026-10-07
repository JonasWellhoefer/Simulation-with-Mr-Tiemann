import numpy as np

from overbooking import analytic
from overbooking.model import HotelParams, simulate_nights, sweep_bookings


def test_pmf_sums_to_one():
    assert abs(sum(analytic.binom_pmf(110, k, 0.9) for k in range(111)) - 1) < 1e-12


def test_no_overbooking_never_denies():
    p = HotelParams()
    _, denied, _ = simulate_nights(p, p.capacity, 1000, np.random.default_rng(0))
    assert denied.sum() == 0


def test_simulation_matches_exact():
    p = HotelParams()
    s = sweep_bookings(p, [105], 40000, seed=1)
    assert abs(s["p_denied"][0] - analytic.prob_denied(p, 105)) < 0.01
    exact = analytic.expected_profit(p, 105)
    assert abs(s["mean_profit"][0] - exact) < 4 * s["se_profit"][0]


def test_overbooking_beats_none():
    p = HotelParams()
    assert analytic.optimal_bookings(p) > p.capacity
