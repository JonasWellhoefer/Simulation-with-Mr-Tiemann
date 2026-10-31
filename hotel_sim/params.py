"""Parameters of the hotel overbooking model.

All inputs of the simulation live here so that a dashboard only has to build a
``Params`` object (``dataclasses.replace(params, overbooking_level=0.15)`` for
tweaks) and call ``simulate`` / ``run_replications``.
"""
from dataclasses import dataclass, field
from typing import Tuple


@dataclass(frozen=True)
class Segment:
    """A customer segment with its own behaviour."""
    name: str
    share: float                 # share of booking requests (shares are normalised)
    price: float                 # revenue per room and night
    noshow_prob: float           # mean probability that a booking does not show up
    cancel_prob: float           # probability that the booking is cancelled before arrival
    mean_stay: float = 2.0       # nights, stay = 1 + Poisson(mean_stay - 1)
    mean_lead: float = 15.0      # days between booking and arrival (exponential)
    group_prob: float = 0.0      # probability that a request is a group booking
    group_size_mean: float = 3.0  # rooms of a group, = 2 + Poisson(mean - 2)


DEFAULT_SEGMENTS = (
    Segment("business", 0.35, 140.0, noshow_prob=0.08, cancel_prob=0.15,
            mean_stay=2.0, mean_lead=10.0),
    Segment("leisure", 0.40, 110.0, noshow_prob=0.10, cancel_prob=0.25,
            mean_stay=3.0, mean_lead=30.0, group_prob=0.10, group_size_mean=3.0),
    Segment("online portal", 0.25, 90.0, noshow_prob=0.18, cancel_prob=0.40,
            mean_stay=2.0, mean_lead=20.0),
)


@dataclass(frozen=True)
class Params:
    # --- hotel and policy -------------------------------------------------
    capacity: int = 100
    overbooking_level: float = 0.10   # accept bookings up to capacity * (1 + level)
    denied_cost: float = 250.0        # compensation per room that cannot be provided

    # --- demand (2.1 dynamics) --------------------------------------------
    demand_rate: float = 62.0         # mean booking requests per arrival day
    weekday_factors: Tuple[float, ...] = (0.90, 0.95, 1.00, 1.05, 1.20, 1.25, 0.95)
    season_amplitude: float = 0.0     # relative amplitude of a sinusoidal season
    season_length: int = 90           # days per season cycle
    walkin_rate: float = 2.0          # mean walk-in guests per night (fill free rooms)
    walkin_price: float = 100.0

    segments: Tuple[Segment, ...] = DEFAULT_SEGMENTS

    # --- randomness (2.2) ---------------------------------------------------
    # Coefficient of variation of a shared per-day "shock" that scales every
    # no-show probability of that arrival day (weather, strike, event...).
    # 0 = guests are independent.
    shock_cv: float = 0.0

    # --- simulation horizon -------------------------------------------------
    n_days: int = 180                 # evaluated nights
    warmup_days: int = 10             # discarded start-up nights
    def __post_init__(self):
        if type(self.capacity) is not int or self.capacity <= 0:
            raise ValueError("Capacity must be a positive integer.")
    @property
    def booking_limit(self) -> int:
        return int(self.capacity * (1 + self.overbooking_level) + 1e-9)

    @classmethod
    def binomial_baseline(cls, capacity=100, bookings=109, show_prob=0.9,
                          revenue=120.0, denied_cost=250.0, n_days=2000):
        """Degenerate parameter set that reduces the model to the textbook
        case: one night stays, single rooms, no cancellations, no shocks,
        no walk-ins, and demand far above the limit so that exactly
        ``bookings`` rooms are booked per night. Arrivals ~ Binomial(bookings, p).
        """
        seg = Segment("baseline", 1.0, revenue, noshow_prob=1 - show_prob,
                      cancel_prob=0.0, mean_stay=1.0, mean_lead=10.0)
        return cls(capacity=capacity, overbooking_level=bookings / capacity - 1,
                   denied_cost=denied_cost, demand_rate=4 * bookings,
                   weekday_factors=(1.0,) * 7, walkin_rate=0.0,
                   segments=(seg,), shock_cv=0.0, n_days=n_days, warmup_days=5)
