"""Hotel overbooking simulation: model core.

Public interface (what a dashboard needs):

    from hotel_sim import Params, Segment, simulate, run_replications

    params = Params(overbooking_level=0.12, shock_cv=0.15)
    one_run = simulate(params, seed=1)               # nightly time series
    study = run_replications(params, n_runs=50)      # aggregated results with CIs
"""
from .params import Params, Segment
from .model import RunResult, simulate
from .experiments import run_replications, sweep

__all__ = ["Params", "Segment", "RunResult", "simulate", "run_replications", "sweep"]
