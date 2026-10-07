# Project Proposal: Hotel Overbooking Simulation

*Status: draft for team discussion – nothing in here is implemented yet.*

## 1. Motivation and added value
Hotels sell more rooms than they have because some guests do not show up. Too little
overbooking leaves rooms empty; too much forces the hotel to turn guests away and pay
compensation. The question is: **how many bookings should a hotel accept to maximise
expected profit at an acceptable risk?**

The current baseline (already in the repo) models a single night with independent guests,
so arrivals ~ Binomial(N, p). It can be solved exactly, which makes it a good **validation
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

## 5. Open questions for the team
- Which extensions do we commit to? (Suggestion: 2.1 + 2.2 + the statistics parts of 2.3)
- Python only, or Julia for performance-critical parts?
- How do we split the work?
- Do we want an interactive demo (sliders) for the presentation?

## 6. Suggested split (to be discussed)
| Area | Owner |
|------|-------|
| Dynamic booking/cancellation model |  |
| Correlated no-shows, groups, segments |  |
| Statistics, validation, sensitivity |  |
| Presentation and documentation |  |
