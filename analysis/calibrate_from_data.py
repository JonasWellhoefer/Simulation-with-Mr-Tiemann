"""Reproduce the segment parameters in ``hotel_sim/params.py`` from the
"Hotel booking demand" dataset (Antonio, de Almeida & Nunes 2019, Data in
Brief 22, 41-49, https://doi.org/10.1016/j.dib.2018.11.126, CC BY 4.0).

The data is not stored in this repo. Download the CSV, e.g. the TidyTuesday
mirror (2020-02-11, hotels.csv):
https://raw.githubusercontent.com/rfordatascience/tidytuesday/master/data/2020/2020-02-11/hotels.csv

Usage:  python analysis/calibrate_from_data.py path/to/hotels.csv
Needs pandas (installed with the dashboard requirements).
"""
import sys

import numpy as np
import pandas as pd

SEGMENTS = {"Corporate": "business", "Aviation": "business",
            "Direct": "leisure", "Offline TA/TO": "leisure", "Groups": "leisure",
            "Online TA": "online portal"}
MONTHS = {m: i + 1 for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August",
     "September", "October", "November", "December"])}


def main(path):
    df = pd.read_csv(path)
    city = df[df.hotel == "City Hotel"].copy()
    print(f"City hotel bookings: {len(city)}")
    city["segment"] = city.market_segment.map(SEGMENTS)
    city = city.dropna(subset=["segment"])

    print("\nSegment shares:")
    print(city.segment.value_counts(normalize=True).round(3).to_string())

    print("\nPer segment: cancellation rate, no-show rate (of non-cancelled),"
          " mean lead time and length of stay (arrived), mean ADR (arrived, ADR > 0)")
    for name, g in city.groupby("segment"):
        arrived = g[g.reservation_status == "Check-Out"]
        not_cancelled = g[g.reservation_status != "Canceled"]
        stay = arrived.stays_in_weekend_nights + arrived.stays_in_week_nights
        print(f"  {name:14s} cancel {(g.reservation_status == 'Canceled').mean():.3f}"
              f"  no-show {(not_cancelled.reservation_status == 'No-Show').mean():.3f}"
              f"  lead {arrived.lead_time.mean():6.1f}  stay {stay.mean():.2f}"
              f"  ADR {arrived[arrived.adr > 0].adr.mean():6.1f}")

    # timing of cancellations: share of the way from booking to arrival
    canc = city[(city.reservation_status == "Canceled") & (city.lead_time > 0)]
    arrival = pd.to_datetime(dict(year=canc.arrival_date_year,
                                  month=canc.arrival_date_month.map(MONTHS),
                                  day=canc.arrival_date_day_of_month))
    days_before = (arrival - pd.to_datetime(canc.reservation_status_date)).dt.days
    share = (1 - days_before / canc.lead_time).clip(0, 1)
    m, v = share.mean(), share.var()
    k = m * (1 - m) / v - 1
    print(f"\nCancellation timing (n={len(share)}): mean share {m:.3f}, "
          f"Beta fit (method of moments) a={m * k:.2f}, b={(1 - m) * k:.2f}")
    print("Histogram (10 bins from booking to arrival):",
          np.histogram(share, bins=10, range=(0, 1))[0].tolist())


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
