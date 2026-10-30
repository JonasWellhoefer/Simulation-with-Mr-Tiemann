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
- [x] Choose topic: hotel overbooking (scope: PROPOSAL.md 2.1 + 2.2, interactive dashboard)
- [ ] Language: mainly Python, possibly Julia
- [ ] Implement simulation
- [ ] Validate against analytical values
- [ ] Build presentation
- [ ] Contribution overview per person

## Model core (`hotel_sim/`)
```
pip install -r requirements.txt
python examples/run_example.py   # overbooking level x correlated no-shows
pytest
```
Interface for the dashboard:
```python
from dataclasses import replace
from hotel_sim import Params, simulate, run_replications, sweep

params = Params(overbooking_level=0.12, shock_cv=0.3)
run = simulate(params, seed=1)           # nightly arrays: occupied, denied, profit, ...
study = run_replications(params, 30)     # means, 95% CIs, VaR/CVaR of nightly profit
curve = sweep(params, "overbooking_level", [0, .05, .1, .15, .2])
```
- `params.py` – all inputs (`Params`, customer `Segment`s); dashboard sliders map 1:1 to fields
- `model.py` – event-based simulation (2.1 booking/cancellation dynamics, multi-night stays,
  walk-ins; 2.2 segments, groups, shared no-show shock `shock_cv`)
- `experiments.py` – replications with confidence intervals, risk measures, parameter sweeps
- `analytic.py` + `Params.binomial_baseline()` – the degenerate case reproduces the exact
  binomial results (validation test in `tests/`)

## Contributions
| Person | Tasks |
|--------|-------|
| Jonas, Vrinda | Code (model, dashboard) |
| Viveca | Presentation |

*Note: The lecture slides are not meant to be shared outside ISM (see imprint), so they are not included in this repo.*

