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
- [x] Form group (by Nov 9)
- [x] Choose topic: hotel overbooking (scope: PROPOSAL.md 2.1 + 2.2, interactive dashboard)
- [x] Language: Python
- [x] Implement simulation (`hotel_sim/`, extensions 2.1 + 2.2)
- [x] Validate against analytical values (binomial comparison + chi-square test)
- [x] Sources for the model assumptions (ASSUMPTIONS.md)
- [x] Interactive dashboard (`dashboard.py`)
- [ ] Build presentation
- [x] Contribution overview per person
- [x] Code walkthrough guide for the presentation (docs/CODE_WALKTHROUGH.md)

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
- `params.py` – all inputs (`Params`, customer `Segment`s); dashboard sliders map 1:1 to fields.
  Default values and their sources: [ASSUMPTIONS.md](ASSUMPTIONS.md)
- `model.py` – event-based simulation (2.1 booking/cancellation dynamics, multi-night stays,
  walk-ins; 2.2 segments, groups, shared no-show shock `shock_cv`)
- `experiments.py` – replications with confidence intervals, risk measures, parameter sweeps
- `analytic.py` + `Params.binomial_baseline()` – the degenerate case reproduces the exact
  binomial results (validation test in `tests/`)

## Analysis (`analysis/`)
```
python analysis/run_analysis.py           # full run, about 2-3 minutes
python analysis/run_analysis.py --quick   # low precision, for testing
```
Writes figures and `results.md` to `analysis/output/`:
1. validation against the exact binomial model, incl. a chi-square goodness-of-fit test
2. optimal overbooking level, denial risk and CVaR, with and without correlated no-shows
3. textbook binomial formula vs. simulated optimum
4. sensitivity of the optimal level to cancellation rate and denied cost
5. convergence of the estimate over the number of runs

`analysis/calibrate_from_data.py` reproduces the segment parameters from the public
hotel booking dataset (see ASSUMPTIONS.md).

## Contributions
| Person | Contributions | Main files / pull requests |
|--------|---------------|----------------------------|
| Jonas | Project setup and coordination, simulation model (booking dynamics, segments, correlated no-shows), calibration with real hotel data and sources, statistical analysis (validation, chi-square test, sensitivity, confidence intervals), dashboard extensions (overbooking comparison, market assumptions), code reviews | `hotel_sim/`, `analysis/`, `ASSUMPTIONS.md`, `docs/CODE_WALKTHROUGH.md`; PRs 5, 8, 9 |
| Vrinda | Input validation with tests, interactive Streamlit dashboard (controls, results table, charts), code review of the model | `hotel_sim/params.py` (validation), `tests/`, `dashboard.py`; PRs 6, 7 |
| Viveca | Presentation: slides, structure, code walkthrough and live demo | presentation; `docs/CODE_WALKTHROUGH.md` as preparation |

Jonas's code was developed with the AI coding assistant Claude Code; the commits are marked
with "Co-Authored-By". The full history of who changed what is in the
[pull requests](https://github.com/JonasWellhoefer/Simulation-with-Mr-Tiemann/pulls?q=is%3Apr).

*Note: The lecture slides are not meant to be shared outside ISM (see imprint), so they are not included in this repo.*

## Interactive dashboard

Install the dependencies and launch the dashboard from the project folder:

```bash
python3 -m pip install -r requirements.txt
python3 -m streamlit run dashboard.py
```

Choose the room capacity, overbooking allowance, simulation days, number
of runs, shared no-show shock strength and the market assumptions (booking
requests, no-show rate, cancellation rate, cost per denied room), then click **Run simulation**.

The dashboard displays average nightly profit (with 95% confidence interval),
occupancy, nights with denied rooms, a comparison of profit and denial risk
across overbooking levels with the best level highlighted, a results table and
a profit chart by simulation run.

