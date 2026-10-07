"""Monte Carlo simulation of hotel overbooking for a single night.

Model
-----
The hotel has ``capacity`` rooms and accepts ``bookings`` reservations.
Each reservation shows up independently with probability ``show_prob``.
Arrivals ~ Binomial(bookings, show_prob).

* Every guest who gets a room earns ``room_revenue``.
* Every guest who arrives but cannot be accommodated ("denied") costs
  ``denied_cost`` (compensation, relocation, goodwill).
"""
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class HotelParams:
    capacity: int = 100
    show_prob: float = 0.90
    room_revenue: float = 120.0
    denied_cost: float = 250.0


def simulate_nights(params: HotelParams, bookings: int, n_nights: int,
                    rng: np.random.Generator):
    """Simulate ``n_nights`` independent nights.

    Returns (arrivals, denied, profit) as arrays of length ``n_nights``.
    Show-ups are drawn guest by guest (Bernoulli) so the code mirrors the
    real process instead of calling a binomial shortcut.
    """
    shows = rng.random((n_nights, bookings)) < params.show_prob
    arrivals = shows.sum(axis=1)
    seated = np.minimum(arrivals, params.capacity)
    denied = np.maximum(arrivals - params.capacity, 0)
    profit = seated * params.room_revenue - denied * params.denied_cost
    return arrivals, denied, profit


def sweep_bookings(params: HotelParams, booking_levels, n_nights: int,
                   seed: int = 42):
    """Run the simulation for each booking level.

    Returns a dict of arrays: mean profit, standard error, P(at least one
    guest denied) and mean number of denied guests.
    """
    rng = np.random.default_rng(seed)
    out = {k: [] for k in ("mean_profit", "se_profit", "p_denied", "mean_denied")}
    for n in booking_levels:
        _, denied, profit = simulate_nights(params, int(n), n_nights, rng)
        out["mean_profit"].append(profit.mean())
        out["se_profit"].append(profit.std(ddof=1) / np.sqrt(n_nights))
        out["p_denied"].append((denied > 0).mean())
        out["mean_denied"].append(denied.mean())
    return {k: np.array(v) for k, v in out.items()}
