# Simulation – Exam Project (Mr. Tiemann, ISM)

## Task (per the "Exam" slide)
- Exam type: presentation, roughly 45 minutes
- Groups of 2–3 people (no more than 3)
- Presentation dates: Nov 19 and Nov 26 – **groups must be reported by Nov 9 at the latest**

Deliverables:
1. Pick an appropriate simulation, code it, document it, present it
2. Describe the simulation: its purpose and added value
3. Walk through the code
4. Run the simulation live
5. Explain and interpret the results
6. If possible, match the simulation results against analytical probabilities
7. Make clear how and what every group member contributed

## Status
- [ ] Form group (by Nov 9)
- [x] Choose topic: hotel overbooking
- [ ] Language: mainly Python, possibly Julia
- [x] Implement simulation (first version)
- [x] Validate against analytical values (binomial, first version)
- [ ] Build presentation
- [ ] Contribution overview per person

## Hotel overbooking simulation (Python)
A hotel with `capacity` rooms accepts `N` bookings. Each guest shows up independently
with probability `p`, so arrivals ~ Binomial(N, p). Guests with a room earn revenue,
guests who arrive but cannot be housed cost compensation. Question: how many bookings
maximise expected profit?

```
pip install -r requirements.txt
python run_simulation.py --nights 20000   # prints table, saves results/overbooking.png
pytest                                    # checks simulation against exact binomial results
```

- `overbooking/model.py` – Monte Carlo simulation (guest-by-guest Bernoulli draws)
- `overbooking/analytic.py` – exact binomial results to validate against
- `run_simulation.py` – sweep over booking levels, comparison table and plot

Default result (100 rooms, p = 0.9, revenue 120, denied cost 250): optimum at 109 bookings
in both simulation and exact calculation (expected profit about 11,592 vs. 10,800 without overbooking).

Ideas to extend: random group sizes, cancellations over time, overall demand limit,
different room types, sensitivity to `p` and the denied cost.

## Contributions
| Person | Tasks |
|--------|-------|
|        |       |

*Note: The lecture slides are not meant to be shared outside ISM (see imprint), so they are not included in this repo.*

<!-- PR/merge test: harmless change -->
