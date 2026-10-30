"""Replications and parameter sweeps on top of :func:`simulate`."""
from dataclasses import replace

import numpy as np

from .model import simulate
from .params import Params

METRICS = ("mean_profit", "std_profit", "mean_revenue", "mean_occupancy",
           "mean_denied", "p_denied", "mean_noshow_rate")


def run_replications(params: Params, n_runs: int = 30, seed: int = 0) -> dict:
    """Independent runs with reproducible seeds.

    Returns for each metric the mean over runs and a 95% confidence interval,
    plus ``nightly_profit`` (all nights of all runs) and the tail risk
    ``var_5`` / ``cvar_5`` of the nightly profit (5% worst nights).
    """
    seeds = np.random.SeedSequence(seed).spawn(n_runs)
    summaries, nightly = [], []
    for s in seeds:
        res = simulate(params, seed=s)
        summaries.append(res.summary())
        nightly.append(res.profit)
    nightly = np.concatenate(nightly)

    out = {"n_runs": n_runs, "params": params}
    for m in METRICS:
        v = np.array([x[m] for x in summaries])
        half = 1.96 * v.std(ddof=1) / np.sqrt(n_runs) if n_runs > 1 else np.nan
        out[m] = {"mean": float(v.mean()), "ci95": (float(v.mean() - half),
                                                    float(v.mean() + half)),
                  "runs": v}
    var5 = float(np.quantile(nightly, 0.05))
    out["nightly_profit"] = nightly
    out["var_5"] = var5
    out["cvar_5"] = float(nightly[nightly <= var5].mean())
    return out


def sweep(params: Params, field: str, values, n_runs: int = 20, seed: int = 0):
    """Study one parameter, e.g. ``sweep(p, "overbooking_level", [0, .05, .1])``.
    Returns a list of (value, result of run_replications)."""
    return [(v, run_replications(replace(params, **{field: v}), n_runs, seed))
            for v in values]
