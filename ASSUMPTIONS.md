# Model Assumptions and Sources

All default values live in `hotel_sim/params.py`. This file explains where each one comes
from. Reliability: **PR** peer-reviewed, **OFF** official statistic or authority,
**ASSOC** industry association, **IND** industry report, **WEB** blog / practitioner article,
**ASSUMPTION** our own choice without a source.

## 1. Customer segments (city hotel data)

Main source: the "Hotel booking demand" dataset, Antonio, de Almeida & Nunes (2019),
*Data in Brief* 22, 41–49, https://doi.org/10.1016/j.dib.2018.11.126 (**PR**, open data,
CC BY 4.0). We use the city hotel (Lisbon, 79,330 bookings, arrivals 07/2015–08/2017) and
computed the values ourselves; `python analysis/calibrate_from_data.py hotels.csv`
reproduces them.

Mapping of the dataset's market segments: business = Corporate + Aviation,
leisure = Direct + Offline TA/TO + Groups, online portal = Online TA.

| Parameter | Business | Leisure | Online portal | Measure |
|---|---:|---:|---:|---|
| Share of booking requests | 0.05 | 0.45 | 0.50 | share of bookings (0.041 / 0.467 / 0.492) |
| Cancellation rate | 19.8% | 47.4% | 36.2% | cancelled bookings / all bookings |
| No-show rate | 2.2% | 2.0% | 1.8% | no-shows / non-cancelled bookings |
| Mean lead time (days) | 16.7 | 102.1 | 72.0 | booking to arrival, arrived bookings |
| Mean length of stay (nights) | 2.02 | 2.85 | 3.11 | arrived bookings |
| Price per night (€) | 84 | 99 | 100 | mean ADR of arrived bookings; online portal: 118 minus 15% commission |

**Cancellation timing:** for the 31,951 cancelled bookings we measured *when* they cancel,
as a share of the time between booking and arrival. The distribution is U-shaped:
31% cancel within the first tenth of that time, 9% in the last tenth. Method-of-moments
fit: **Beta(0.41, 0.70)** (`cancel_timing_a`, `cancel_timing_b`).

**Plausibility checks for Germany:**
- Average room rate 2025: **€109**, occupancy **68.1%** (IHA, *Hotelmarkt Deutschland 2026*,
  press release 13 May 2026, **ASSOC**,
  https://www.hotellerie.de/fileadmin/user_upload/Dokumente/Pressemitteilungen/PM_2026-05-13_IHA-Branchenreport_Hotelmarkt_Deutschland_2026_erschienen.pdf).
  Our prices (€84–118) are in the same range.
- Length of stay in German hotels: about **2.0 nights** (Destatis via bulwiengesa
  *Hotelstudie 2019*, **OFF**). Our 2–3 nights are slightly higher, as in the Lisbon data.
- Room occupancy, all German hotels with 25+ rooms: **60.4%** in 2025 (Destatis via DEHOGA
  *Zahlenspiegel IV/2025*, **OFF**). City hotels are higher, see IHA above.

**Limitation:** the data comes from one Portuguese city hotel before COVID. We found no
German data with this level of detail.

## 2. Prices and costs

| Parameter | Value | Source |
|---|---|---|
| Online portal commission | 15% | Booking.com standard commission in Germany 10–15%, effective 20–25% according to IHA: Bundeskartellamt decision B9-121/13 (2015), **OFF**, https://www.bundeskartellamt.de/SharedDocs/Entscheidung/DE/Entscheidungen/Kartellverbot/2015/B9-121-13.pdf. Basic OTA commission 10–20%: European Commission (2022), *Market study on the distribution of hotel accommodation in the EU*, **OFF** |
| Cost per denied room (`denied_cost`) | €250 (≈ 2.5 × room rate) | Usual practice: the hotel pays the first night in a comparable hotel plus transport (e.g. IHG policy, **WEB**); in Germany the guest can claim the extra cost of an equivalent hotel and transfer (§§ 280 ff. BGB, **WEB** legal advice). Rule of thumb "walk cost ≈ 2× the cost of an empty room": Kimes, eCornell (2013), **WEB** by a Cornell professor. Walked guests also become less loyal: Noone & Lee (2011), *J. Hospitality & Tourism Research* 35(3), **PR**. No peer-reviewed euro estimate exists, so we test 100–1000 in the sensitivity analysis |

## 3. Demand and model structure

| Parameter | Value | Source |
|---|---|---|
| Booking requests per day (`demand_rate`) | 38 | **Calibrated** so that occupancy is about 73% (IHA 68.1% for Germany; city hotels typically 65–75%) |
| Season (`season_amplitude`, `season_length`) | ±30%, 90-day cycle | **ASSUMPTION**, creates high- and low-demand periods |
| Weekday pattern | 0.90–1.25 | **ASSUMPTION** |
| Group bookings | 10% of leisure requests, 3 rooms on average | **ASSUMPTION**. The data has 17.6% group bookings but no group size; STR defines a group as 10+ rooms |
| Walk-in guests | 2 per night at €100 | **ASSUMPTION** |
| Lead time distribution | exponential with the mean above | **ASSUMPTION**, consistent with the right-skewed data (median below mean) |
| Length of stay distribution | 1 + Poisson(mean − 1) | **ASSUMPTION** |
| Shared no-show shock (`shock_cv`) | 0 (scenarios 0.3 and 0.6) | **Scenario**, not estimated |

## 4. Plausibility of the results

A survey of 365 US hotels found the best RevPAR with overbooking **below 5% of capacity**,
and lower RevPAR when hotels overbooked by more than 10% (Riasi 2018, PhD dissertation,
University of Delaware, https://udspace.udel.edu/items/b2eefd99-8e27-4927-b6be-996c3b264b1e).
Our simulated optimum of 5–7.5% is close to this. Note that our overbooking level is a
booking limit on rooms on the books, so it is not exactly the same measure.

Vendor blogs mention no-show rates of 5–15% without any method. We do not use them; the
dataset and D-EDGE (2024, "commonly 1–5%", **WEB**) both point to about 2%.
