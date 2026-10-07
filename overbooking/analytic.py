"""Exact (analytical) results for the overbooking model.

With N bookings and show probability p, arrivals A ~ Binomial(N, p), so
P(A = k), E[denied] and E[profit] can be computed exactly and compared with
the Monte Carlo estimates.
"""
from math import comb

from .model import HotelParams


def binom_pmf(n: int, k: int, p: float) -> float:
    return comb(n, k) * p**k * (1 - p) ** (n - k)


def prob_denied(params: HotelParams, bookings: int) -> float:
    """P(arrivals > capacity)."""
    return sum(binom_pmf(bookings, k, params.show_prob)
               for k in range(params.capacity + 1, bookings + 1))


def expected_denied(params: HotelParams, bookings: int) -> float:
    return sum((k - params.capacity) * binom_pmf(bookings, k, params.show_prob)
               for k in range(params.capacity + 1, bookings + 1))


def expected_profit(params: HotelParams, bookings: int) -> float:
    exp_arrivals = bookings * params.show_prob
    exp_denied = expected_denied(params, bookings)
    exp_seated = exp_arrivals - exp_denied
    return exp_seated * params.room_revenue - exp_denied * params.denied_cost


def optimal_bookings(params: HotelParams, max_extra: int = 60) -> int:
    """Booking level maximising exact expected profit."""
    levels = range(params.capacity, params.capacity + max_extra + 1)
    return max(levels, key=lambda n: expected_profit(params, n))
