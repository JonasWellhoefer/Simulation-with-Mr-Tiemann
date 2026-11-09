# Project Proposal: Hotel Overbooking Simulation

*Status: scope agreed with the team; 2.1 and 2.2 are implemented in `hotel_sim/`, the analysis in `analysis/`, the dashboard is in progress (see section 7).*

## 1. Motivation and added value
Hotels sell more rooms than they have because some guests do not show up. Too little
overbooking leaves rooms empty; too much forces the hotel to turn guests away and pay
compensation. The question is: **how many bookings should a hotel accept to maximise
expected profit at an acceptable risk?**

The simplest version of the model (`Params.binomial_baseline()`) covers a single night with
independent guests, so arrivals ~ Binomial(N, p). It can be solved exactly, which makes it a good **validation
case** but not a convincing reason to simulate. The extensions below move to settings
where no closed-form solution exists, so simulation adds real value.

## 2. Planned extensions

### 2.1 Dynamics over time (event-based simulation)
- Bookings arrive over several weeks (Poisson process, possibly with weekday/season pattern).
- Cancellations follow a time-dependent distribution (rising shortly before arrival).
- Multi-night stays couple the nights: a guest staying 3 nights occupies a room on
  several days, so overbooking on one night affects the following nights.
- Walk-in guests may fill rooms that stay empty.

### 2.2 More realistic randomness
- **Uncertain / correlated no-show rate:** p itself is random (e.g. Beta-distributed per
  night) to model shared shocks such as weather, strikes or events. Guests are then
  no longer independent.
- **Group bookings:** a group shows up completely or not at all.
- **Customer segments** (business, leisure, online portals) with their own no-show rates.
- Goal: show how much the simple binomial formula **underestimates the risk** once
  these effects are included.

### 2.3 Statistical analysis (parts of the course content)
- Confidence intervals and convergence of the estimates over the number of runs.
- Variance reduction (antithetic variables, common random numbers) for fair strategy
  comparison.
- Hypothesis tests: is strategy A significantly better than strategy B?
- Sensitivity analysis over p and the cost ratio (heatmap of the optimal booking level).
- Risk measures (e.g. VaR / CVaR of nightly profit), not just the expected value.

## 3. Validation
The simplified special case (one night, independent guests, fixed p) must reproduce the
exact binomial results. Extensions are compared against this baseline to quantify their effect.

## 4. Deliverables for the exam
- Documented Python code (structure: model, analytic baseline, experiments, tests)
- Live run of the simulation during the presentation
- Interpretation of the results and comparison with the analytical probabilities
- Contribution table per team member (see README)

## 5. Decisions (team discussion)
- **Scope:** extensions 2.1 (dynamics over time) and 2.2 (more realistic randomness).
  Parts of 2.3 (confidence intervals, sensitivity) only as needed to interpret results.
- **Final deliverable:** an interactive dashboard to run and explore the simulation live.
- **Language:** Python (Julia only if a clear need appears).

## 6. Roles
| Area | Owner |
|------|-------|
| Code: simulation model, dashboard | Jonas, Vrinda |
| Presentation | Viveca |

## 7. Status
Done:
- Model core for 2.1 and 2.2 (`hotel_sim/`), input validation and tests
- Shared interface for the dashboard: `Params` in, `simulate` / `run_replications` / `sweep` out
- Analysis (`analysis/`): validation against the binomial model incl. chi-square test,
  optimal overbooking level, risk (CVaR), textbook formula vs. simulation, sensitivity,
  convergence
- Dashboard framework: Streamlit

Open:
- Dashboard: profit vs. overbooking chart and further controls
- Sources for the model assumptions
- Presentation
- Group registration (deadline Nov 9)
