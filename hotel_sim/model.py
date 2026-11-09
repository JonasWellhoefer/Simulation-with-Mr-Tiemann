"""Event-based simulation of a hotel with overbooking.

One call of :func:`simulate` is one run over ``warmup_days + n_days`` nights.

Process
-------
1. **Demand (2.1).** For every arrival day a Poisson number of booking
   requests is generated (weekday/season pattern). Each request has a
   segment, a lead time, a length of stay, a size (1 room or a group) and
   may be cancelled later (timing between booking and arrival ~ Beta, fitted
   to real hotel data: many cancel soon after booking, some just before arrival).
2. **Booking phase.** Requests and cancellations are processed in time
   order. A request is accepted if on every night of the stay the rooms on
   the books stay <= ``booking_limit``. Cancellations free capacity again.
3. **Operations phase.** Night by night: guests who are already in house keep
   their room, arriving guests are served in random order, a booking that
   does not fit is *denied* (whole group, whole stay) and costs
   ``denied_cost``. Remaining rooms go to walk-ins.
   Because stays span several nights, a denied or accepted guest changes the
   following nights (nights are coupled).
4. **Randomness (2.2).** Bookings are *not* independent if ``shock_cv > 0``:
   every arrival day draws a shared shock that scales all no-show
   probabilities of that day. Groups show up completely or not at all.
"""
from dataclasses import dataclass

import numpy as np

from .params import Params


@dataclass
class RunResult:
    """Nightly time series of one run (arrays have length ``n_days``)."""
    on_the_books: np.ndarray    # rooms booked for the night (after cancellations)
    occupied: np.ndarray        # rooms actually occupied
    denied: np.ndarray          # rooms of denied guests (arriving that night)
    revenue: np.ndarray
    profit: np.ndarray
    noshow_rate: np.ndarray     # share of booked rooms that did not arrive (arrival nights)
    params: Params

    def summary(self) -> dict:
        p = self.params
        return {
            "mean_profit": float(self.profit.mean()),
            "std_profit": float(self.profit.std(ddof=1)),
            "mean_revenue": float(self.revenue.mean()),
            "mean_occupancy": float(self.occupied.mean() / p.capacity),
            "mean_denied": float(self.denied.mean()),
            "p_denied": float((self.denied > 0).mean()),
            "mean_noshow_rate": float(np.nanmean(self.noshow_rate)),
        }


def _shocks(params: Params, n: int, rng) -> np.ndarray:
    if params.shock_cv <= 0:
        return np.ones(n)
    k = 1.0 / params.shock_cv ** 2
    return rng.gamma(k, 1.0 / k, size=n)      # mean 1, CV = shock_cv


def simulate(params: Params, seed=None) -> RunResult:
    rng = np.random.default_rng(seed)
    segs = params.segments
    T = params.warmup_days + params.n_days
    cap = params.capacity
    limit = params.booking_limit

    shares = np.array([s.share for s in segs], dtype=float)
    shares /= shares.sum()

    # ---- 1. demand ----------------------------------------------------
    days = np.arange(T)
    lam = (params.demand_rate
           * np.take(params.weekday_factors, days % len(params.weekday_factors))
           * (1 + params.season_amplitude
              * np.sin(2 * np.pi * days / params.season_length)))
    counts = rng.poisson(np.maximum(lam, 0))
    n = int(counts.sum())
    arrival = np.repeat(days, counts)
    seg = rng.choice(len(segs), size=n, p=shares)

    def per_seg(attr):
        return np.array([getattr(s, attr) for s in segs], dtype=float)[seg]

    lead = rng.exponential(per_seg("mean_lead"))
    stay = 1 + rng.poisson(np.maximum(per_seg("mean_stay") - 1, 0))
    is_group = rng.random(n) < per_seg("group_prob")
    rooms = np.where(is_group,
                     2 + rng.poisson(np.maximum(per_seg("group_size_mean") - 2, 0)),
                     1)
    cancels = rng.random(n) < per_seg("cancel_prob")
    t_book = arrival - lead
    # cancellation time: Beta(a, b) share of the way from booking to arrival
    t_cancel = t_book + rng.beta(params.cancel_timing_a, params.cancel_timing_b,
                                 size=n) * lead

    # ---- 2. booking phase -------------------------------------------
    nights = T + int(stay.max() if n else 1) + 1
    committed = np.zeros(nights, dtype=np.int64)
    accepted = np.zeros(n, dtype=bool)
    cancel_idx = np.flatnonzero(cancels)
    ev_time = np.concatenate([t_book, t_cancel[cancel_idx]])
    ev_ref = np.concatenate([np.arange(n), cancel_idx])
    ev_kind = np.concatenate([np.zeros(n, dtype=np.int8),
                              np.ones(len(cancel_idx), dtype=np.int8)])
    for e in np.lexsort((ev_kind, ev_time)):
        i = ev_ref[e]
        a, s, r = arrival[i], stay[i], rooms[i]
        if ev_kind[e] == 0:
            if committed[a:a + s].max() + r <= limit:
                committed[a:a + s] += r
                accepted[i] = True
        elif accepted[i]:
            committed[a:a + s] -= r
            accepted[i] = False                   # cancelled: gone

    # ---- 3. show-ups --------------------------------------------------
    shock = _shocks(params, T, rng)
    p_ns = np.minimum(1.0, per_seg("noshow_prob") * shock[arrival])
    shows = accepted & (rng.random(n) >= p_ns)

    # ---- 4. operations phase -----------------------------------------
    housed = np.zeros(nights, dtype=np.int64)      # rooms in use per night
    revenue = np.zeros(nights)
    denied = np.zeros(nights, dtype=np.int64)
    price = per_seg("price")
    booked_arrivals = np.zeros(T, dtype=np.int64)
    shown_arrivals = np.zeros(T, dtype=np.int64)
    arriving_by_day = [[] for _ in range(T)]
    for i in np.flatnonzero(accepted):
        booked_arrivals[arrival[i]] += rooms[i]
        if shows[i]:
            shown_arrivals[arrival[i]] += rooms[i]
            arriving_by_day[arrival[i]].append(i)

    for d in range(T):
        order = arriving_by_day[d]
        if len(order) > 1:
            order = [order[j] for j in rng.permutation(len(order))]
        for i in order:
            r, s = rooms[i], stay[i]
            if housed[d] + r <= cap:
                housed[d:d + s] += r
                revenue[d:d + s] += r * price[i]
            else:
                denied[d] += r
        walkins = min(rng.poisson(params.walkin_rate), cap - housed[d])
        if walkins > 0:
            housed[d] += walkins
            revenue[d] += walkins * params.walkin_price

    w = slice(params.warmup_days, T)
    with np.errstate(invalid="ignore", divide="ignore"):
        noshow = np.where(booked_arrivals > 0,
                          1 - shown_arrivals / booked_arrivals, np.nan)
    return RunResult(
        on_the_books=committed[w],
        occupied=housed[w],
        denied=denied[w],
        revenue=revenue[w],
        profit=revenue[w] - denied[w] * params.denied_cost,
        noshow_rate=noshow[w],
        params=params,
    )
