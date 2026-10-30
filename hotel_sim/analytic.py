"""Exact binomial results for the simplified baseline case
(see ``Params.binomial_baseline``). Used for validation only."""
from math import comb


def _pmf(n, k, p):
    return comb(n, k) * p ** k * (1 - p) ** (n - k)


def prob_denied(capacity, bookings, show_prob):
    return sum(_pmf(bookings, k, show_prob) for k in range(capacity + 1, bookings + 1))


def expected_denied(capacity, bookings, show_prob):
    return sum((k - capacity) * _pmf(bookings, k, show_prob)
               for k in range(capacity + 1, bookings + 1))


def expected_profit(capacity, bookings, show_prob, revenue, denied_cost):
    den = expected_denied(capacity, bookings, show_prob)
    return (bookings * show_prob - den) * revenue - den * denied_cost
