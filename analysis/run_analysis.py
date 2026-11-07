"""Analysis for the presentation: validation, optimal overbooking, risk and
sensitivity. Writes figures and a results summary to ``analysis/output/``.

Usage (from the project folder):
    python analysis/run_analysis.py           # full run, a few minutes
    python analysis/run_analysis.py --quick   # fewer runs, for testing
"""
import argparse
import sys
from dataclasses import replace
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hotel_sim import Params, run_replications  # noqa: E402
from hotel_sim import analytic  # noqa: E402

OUT = Path(__file__).resolve().parent / "output"
SEED = 2026


def ci_err(res, metric):
    lo, hi = res[metric]["ci95"]
    return (hi - lo) / 2


def scaled_noshow(params, factor):
    """Copy of params with every segment's no-show probability scaled."""
    segs = tuple(replace(s, noshow_prob=min(1.0, s.noshow_prob * factor))
                 for s in params.segments)
    return replace(params, segments=segs)


# --------------------------------------------------------------------------
# 1. Validation against the exact binomial model
# --------------------------------------------------------------------------
def validation(cfg, report):
    bookings = list(range(100, 121, 2))
    sim_profit, sim_err, sim_pden = [], [], []
    for n in bookings:
        res = run_replications(Params.binomial_baseline(bookings=n, n_days=cfg["val_days"]),
                               n_runs=cfg["val_runs"], seed=SEED)
        sim_profit.append(res["mean_profit"]["mean"])
        sim_err.append(ci_err(res, "mean_profit"))
        sim_pden.append(res["p_denied"]["mean"])
    ex_profit = [analytic.expected_profit(100, n, 0.9, 120.0, 250.0) for n in bookings]
    ex_pden = [analytic.prob_denied(100, n, 0.9) for n in bookings]

    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    ax[0].errorbar(bookings, sim_profit, yerr=sim_err, fmt="o", ms=4, label="Simulation (95% CI)")
    ax[0].plot(bookings, ex_profit, "-", label="Exact (binomial)")
    ax[0].set(xlabel="Bookings accepted (100 rooms)", ylabel="Profit per night",
              title="Validation: profit")
    ax[1].plot(bookings, sim_pden, "o", ms=4, label="Simulation")
    ax[1].plot(bookings, ex_pden, "-", label="Exact (binomial)")
    ax[1].set(xlabel="Bookings accepted (100 rooms)", ylabel="P(at least one guest denied)",
              title="Validation: denial risk")
    for a in ax:
        a.legend()
    fig.tight_layout()
    fig.savefig(OUT / "01_validation.png", dpi=150)
    plt.close(fig)

    max_dev = max(abs(s - e) for s, e in zip(sim_pden, ex_pden))
    report.append("## 1. Validation against the binomial model\n")
    report.append("Simplified case: 1-night stays, single rooms, no cancellations, "
                  "independent guests, show probability 0.9, revenue 120, denied cost 250.\n")
    report.append("| Bookings | Profit sim | Profit exact | P(denied) sim | P(denied) exact |")
    report.append("|---:|---:|---:|---:|---:|")
    for n, sp, ep, sd, ed in zip(bookings, sim_profit, ex_profit, sim_pden, ex_pden):
        report.append(f"| {n} | {sp:,.0f} | {ep:,.0f} | {sd:.3f} | {ed:.3f} |")
    report.append(f"\nLargest deviation in P(denied): {max_dev:.3f}. "
                  f"Exact optimum: {bookings[int(np.argmax(ex_profit))]} bookings, "
                  f"simulated optimum: {bookings[int(np.argmax(sim_profit))]}.\n")


# --------------------------------------------------------------------------
# 2. Optimal overbooking level with and without correlated no-shows
# --------------------------------------------------------------------------
def optimum_and_risk(cfg, report):
    levels = np.round(np.arange(0.0, 0.301, 0.025), 3)
    shocks = (0.0, 0.3, 0.6)
    base = Params(n_days=cfg["days"])
    rows = {}
    for cv in shocks:
        rows[cv] = [run_replications(replace(base, overbooking_level=lv, shock_cv=cv),
                                     n_runs=cfg["runs"], seed=SEED) for lv in levels]

    fig, ax = plt.subplots(1, 3, figsize=(15, 4))
    for cv in shocks:
        r = rows[cv]
        lab = "independent" if cv == 0 else f"shared shock CV={cv}"
        ax[0].errorbar(levels * 100, [x["mean_profit"]["mean"] for x in r],
                       yerr=[ci_err(x, "mean_profit") for x in r], marker="o", ms=3,
                       capsize=2, label=lab)
        ax[1].plot(levels * 100, [x["p_denied"]["mean"] for x in r], marker="o", ms=3, label=lab)
        ax[2].plot(levels * 100, [x["cvar_5"] for x in r], marker="o", ms=3, label=lab)
    ax[0].set(xlabel="Overbooking level (%)", ylabel="Mean profit per night",
              title="Profit (95% CI)")
    ax[1].set(xlabel="Overbooking level (%)", ylabel="Share of nights with denied guests",
              title="Denial risk")
    ax[2].set(xlabel="Overbooking level (%)", ylabel="CVaR 5% of nightly profit",
              title="Bad nights (mean of worst 5%)")
    for a in ax:
        a.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "02_optimum_and_risk.png", dpi=150)
    plt.close(fig)

    report.append("## 2. Optimal overbooking level and risk\n")
    report.append(f"Full model (default parameters), {cfg['runs']} runs x {cfg['days']} nights "
                  "per point, same random numbers for every level (common random numbers).\n")
    report.append("| Shock CV | Best level | Profit at best | Profit without overbooking "
                  "| Gain | P(denied) at best | CVaR 5% at best |")
    report.append("|---:|---:|---:|---:|---:|---:|---:|")
    best = {}
    for cv in shocks:
        r = rows[cv]
        prof = [x["mean_profit"]["mean"] for x in r]
        i = int(np.argmax(prof))
        best[cv] = levels[i]
        report.append(f"| {cv} | {levels[i]:.1%} | {prof[i]:,.0f} | {prof[0]:,.0f} "
                      f"| {prof[i] / prof[0] - 1:+.1%} | {r[i]['p_denied']['mean']:.1%} "
                      f"| {r[i]['cvar_5']:,.0f} |")
    report.append("")
    return rows, levels, best


# --------------------------------------------------------------------------
# 3. What the textbook (binomial) formula would recommend
# --------------------------------------------------------------------------
def naive_vs_simulation(cfg, report, rows, levels):
    base = Params(n_days=cfg["days"])
    r0 = rows[0.0][0]                      # no overbooking, independent guests
    show = 1 - r0["mean_noshow_rate"]["mean"]
    shares = np.array([s.share for s in base.segments])
    price = float(np.dot(shares / shares.sum(), [s.price for s in base.segments]))
    n_star = max(range(base.capacity, base.capacity + 60),
                 key=lambda n: analytic.expected_profit(base.capacity, n, show, price,
                                                        base.denied_cost))
    naive_level = n_star / base.capacity - 1

    report.append("## 3. Textbook formula vs. simulation\n")
    report.append(f"A manager using the binomial formula with the observed show-up rate "
                  f"({show:.1%}) and the average price ({price:.0f}) would accept "
                  f"{n_star} bookings for {base.capacity} rooms, i.e. overbook by "
                  f"**{naive_level:.1%}**.\n")
    report.append("| Shock CV | Profit at textbook level | Best level (simulation) "
                  "| Profit at best | Profit lost by using the formula |")
    report.append("|---:|---:|---:|---:|---:|")
    for cv, r in rows.items():
        naive = run_replications(replace(base, overbooking_level=naive_level, shock_cv=cv),
                                 n_runs=cfg["runs"], seed=SEED)["mean_profit"]["mean"]
        prof = [x["mean_profit"]["mean"] for x in r]
        i = int(np.argmax(prof))
        report.append(f"| {cv} | {naive:,.0f} | {levels[i]:.1%} | {prof[i]:,.0f} "
                      f"| {prof[i] - naive:,.0f} per night |")
    report.append("\nThe formula ignores cancellations, multi-night stays, groups and "
                  "correlated no-shows, which is why its recommendation differs from "
                  "the simulated optimum.\n")


# --------------------------------------------------------------------------
# 4. Sensitivity: optimal level vs. no-show rate and denied cost
# --------------------------------------------------------------------------
def sensitivity(cfg, report):
    factors = (0.5, 1.0, 1.5, 2.0)
    costs = (100.0, 250.0, 500.0, 1000.0)
    levels = np.round(np.arange(0.0, 0.401, 0.05), 3)
    base = Params(n_days=cfg["days"])
    grid = np.zeros((len(costs), len(factors)))
    for i, c in enumerate(costs):
        for j, f in enumerate(factors):
            p = scaled_noshow(replace(base, denied_cost=c), f)
            prof = [run_replications(replace(p, overbooking_level=lv),
                                     n_runs=cfg["sens_runs"], seed=SEED)["mean_profit"]["mean"]
                    for lv in levels]
            grid[i, j] = levels[int(np.argmax(prof))]

    fig, ax = plt.subplots(figsize=(6, 4.5))
    im = ax.imshow(grid * 100, cmap="viridis", origin="lower", aspect="auto")
    ax.set_xticks(range(len(factors)), [f"x{f}" for f in factors])
    ax.set_yticks(range(len(costs)), [f"{c:.0f}" for c in costs])
    ax.set(xlabel="No-show rate (relative to default)", ylabel="Cost per denied room",
           title="Optimal overbooking level (%)")
    for i in range(len(costs)):
        for j in range(len(factors)):
            ax.text(j, i, f"{grid[i, j] * 100:.0f}", ha="center", va="center", color="white")
    fig.colorbar(im, ax=ax, label="%")
    fig.tight_layout()
    fig.savefig(OUT / "04_sensitivity.png", dpi=150)
    plt.close(fig)

    report.append("## 4. Sensitivity of the optimal overbooking level\n")
    report.append(f"Grid search over levels 0-40% in 5% steps, {cfg['sens_runs']} runs per point.\n")
    report.append("| Denied cost \\ no-show factor | " + " | ".join(f"x{f}" for f in factors) + " |")
    report.append("|---:|" + "---:|" * len(factors))
    for i, c in enumerate(costs):
        report.append(f"| {c:.0f} | " + " | ".join(f"{g:.0%}" for g in grid[i]) + " |")
    report.append("\nMore no-shows push the optimal level up, higher compensation "
                  "costs push it down.\n")


# --------------------------------------------------------------------------
# 5. Convergence: how many runs do we need?
# --------------------------------------------------------------------------
def convergence(cfg, report):
    p = Params(n_days=cfg["days"], overbooking_level=0.15)
    res = run_replications(p, n_runs=cfg["conv_runs"], seed=SEED)
    runs = res["mean_profit"]["runs"]
    ns = np.arange(2, len(runs) + 1)
    means = np.array([runs[:k].mean() for k in ns])
    half = np.array([1.96 * runs[:k].std(ddof=1) / np.sqrt(k) for k in ns])

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(ns, means, label="Running mean")
    ax.fill_between(ns, means - half, means + half, alpha=0.3, label="95% CI")
    ax.set(xlabel="Number of simulation runs", ylabel="Mean profit per night",
           title="Convergence of the estimate (overbooking 15%)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / "05_convergence.png", dpi=150)
    plt.close(fig)

    report.append("## 5. Convergence\n")
    report.append("| Runs | Mean profit | 95% CI half-width |")
    report.append("|---:|---:|---:|")
    for k in (5, 10, 20, len(runs)):
        if k <= len(runs):
            report.append(f"| {k} | {means[k - 2]:,.0f} | ±{half[k - 2]:,.0f} |")
    report.append("\nThe half-width shrinks roughly with 1/sqrt(runs).\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="fewer runs, for testing")
    args = ap.parse_args()
    cfg = (dict(runs=4, days=90, val_runs=2, val_days=200, sens_runs=2, conv_runs=8)
           if args.quick else
           dict(runs=20, days=180, val_runs=4, val_days=500, sens_runs=6, conv_runs=40))
    OUT.mkdir(exist_ok=True)

    report = ["# Analysis results\n",
              "Generated by `python analysis/run_analysis.py`"
              + (" --quick (low precision)" if args.quick else "") + ". "
              "All prices and rates are model assumptions (see `hotel_sim/params.py`).\n"]
    print("[validation]", flush=True)
    validation(cfg, report)
    print("[optimum and risk]", flush=True)
    rows, levels, _ = optimum_and_risk(cfg, report)
    print("[textbook vs simulation]", flush=True)
    naive_vs_simulation(cfg, report, rows, levels)
    print("[sensitivity]", flush=True)
    sensitivity(cfg, report)
    print("[convergence]", flush=True)
    convergence(cfg, report)

    (OUT / "results.md").write_text("\n".join(report) + "\n")
    print(f"Done. See {OUT / 'results.md'} and the PNG files next to it.")


if __name__ == "__main__":
    main()
