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
from scipy import stats  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hotel_sim import Params, run_replications, simulate  # noqa: E402
from hotel_sim import analytic  # noqa: E402

OUT = Path(__file__).resolve().parent / "output"
SEED = 2026


def ci_err(res, metric):
    lo, hi = res[metric]["ci95"]
    return (hi - lo) / 2


def scaled_cancellations(params, factor):
    """Copy of params with every segment's cancellation probability scaled.
    Booking requests are scaled too, so that the number of bookings that are
    *not* cancelled stays the same: only the cancellation effect changes."""
    shares = np.array([s.share for s in params.segments])
    shares = shares / shares.sum()
    cancel = np.array([s.cancel_prob for s in params.segments])
    new_cancel = np.minimum(1.0, cancel * factor)
    segs = tuple(replace(s, cancel_prob=float(c))
                 for s, c in zip(params.segments, new_cancel))
    kept_before = float(np.dot(shares, 1 - cancel))
    kept_after = float(np.dot(shares, 1 - new_cancel))
    return replace(params, segments=segs,
                   demand_rate=params.demand_rate * kept_before / kept_after)


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
# 1b. Chi-square goodness-of-fit test of the simulated arrivals
# --------------------------------------------------------------------------
def merge_small_bins(observed, expected, min_expected=5.0):
    """Merge neighbouring categories until every expected count is >= 5
    (rule of thumb for the chi-square test)."""
    obs_bins, exp_bins = [], []
    o_acc = e_acc = 0.0
    for o, e in zip(observed, expected):
        o_acc += o
        e_acc += e
        if e_acc >= min_expected:
            obs_bins.append(o_acc)
            exp_bins.append(e_acc)
            o_acc = e_acc = 0.0
    if e_acc > 0:                       # remaining right tail joins the last bin
        obs_bins[-1] += o_acc
        exp_bins[-1] += e_acc
    return np.array(obs_bins), np.array(exp_bins)


def goodness_of_fit(cfg, report):
    n_book, p_show = 110, 0.9
    ks = np.arange(n_book + 1)
    pmf = stats.binom.pmf(ks, n_book, p_show)
    cases = [("independent guests", 0.0), ("shared no-show shock, CV=0.3", 0.3)]
    rows, hist = [], {}
    for label, cv in cases:
        params = replace(Params.binomial_baseline(bookings=n_book, show_prob=p_show,
                                                  n_days=cfg["gof_days"]), shock_cv=cv)
        res = simulate(params, seed=SEED)
        assert (res.on_the_books == n_book).all(), "baseline must book exactly N rooms"
        arrivals = res.occupied + res.denied   # 1-night stays, no walk-ins
        observed = np.bincount(arrivals, minlength=n_book + 1)
        obs, exp = merge_small_bins(observed, pmf * len(arrivals))
        chi2, p_value = stats.chisquare(obs, exp)
        rows.append((label, len(arrivals), len(obs) - 1, chi2, p_value,
                     arrivals.mean(), arrivals.var(ddof=1)))
        hist[label] = observed / len(arrivals)

    fig, ax = plt.subplots(figsize=(8, 4))
    window = (ks >= 85) & (ks <= 110)
    width = 0.4
    for i, (label, _) in enumerate(cases):
        ax.bar(ks[window] + (i - 0.5) * width, hist[label][window], width=width,
               alpha=0.7, label=f"Simulated: {label}")
    ax.plot(ks[window], pmf[window], "k.-", label=f"Binomial({n_book}, {p_show})")
    ax.axvline(100, ls="--", c="gray", lw=1)
    ax.set(xlabel="Guests arriving (110 bookings, 100 rooms)", ylabel="Relative frequency",
           title="Chi-square test: simulated arrivals vs. binomial distribution")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "01b_chi_square.png", dpi=150)
    plt.close(fig)

    report.append("### Chi-square goodness-of-fit test\n")
    report.append(f"H0: the number of arriving guests per night follows Binomial({n_book}, "
                  f"{p_show}). Categories with an expected count below 5 are merged; "
                  "no parameters are estimated, so df = categories - 1.\n")
    report.append("| Case | Nights | df | Chi-square | p-value | Mean | Variance |")
    report.append("|---|---:|---:|---:|---:|---:|---:|")
    for label, n, df, chi2, pv, m, v in rows:
        pv_txt = f"{pv:.3f}" if pv >= 0.001 else "< 0.001"
        report.append(f"| {label} | {n} | {df} | {chi2:.1f} | {pv_txt} | {m:.2f} | {v:.2f} |")
    report.append(f"\nBinomial mean {n_book * p_show:.2f}, variance "
                  f"{n_book * p_show * (1 - p_show):.2f}. At the 5% level H0 is "
                  + ("not rejected" if rows[0][4] >= 0.05 else "rejected")
                  + " for independent guests and "
                  + ("rejected" if rows[1][4] < 0.05 else "not rejected")
                  + " when guests share a no-show shock: correlated no-shows make arrivals "
                  "more variable than the binomial model assumes.\n")


# --------------------------------------------------------------------------
# 2. Optimal overbooking level with and without correlated no-shows
# --------------------------------------------------------------------------
def optimum_and_risk(cfg, report):
    levels = np.round(np.arange(0.0, 0.251, 0.025), 3)
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
    factors = (0.5, 0.75, 1.0, 1.25, 1.5)
    costs = (100.0, 250.0, 500.0, 1000.0)
    levels = np.round(np.arange(0.0, 0.301, 0.025), 3)
    base = Params(n_days=cfg["days"])
    grid = np.zeros((len(costs), len(factors)))
    for i, c in enumerate(costs):
        for j, f in enumerate(factors):
            p = scaled_cancellations(replace(base, denied_cost=c), f)
            prof = [run_replications(replace(p, overbooking_level=lv),
                                     n_runs=cfg["sens_runs"], seed=SEED)["mean_profit"]["mean"]
                    for lv in levels]
            grid[i, j] = levels[int(np.argmax(prof))]

    fig, ax = plt.subplots(figsize=(6, 4.5))
    im = ax.imshow(grid * 100, cmap="viridis", origin="lower", aspect="auto")
    ax.set_xticks(range(len(factors)), [f"x{f}" for f in factors])
    ax.set_yticks(range(len(costs)), [f"{c:.0f}" for c in costs])
    ax.set(xlabel="Cancellation rate (relative to default)", ylabel="Cost per denied room",
           title="Optimal overbooking level (%)")
    for i in range(len(costs)):
        for j in range(len(factors)):
            ax.text(j, i, f"{grid[i, j] * 100:.1f}", ha="center", va="center", color="white")
    fig.colorbar(im, ax=ax, label="%")
    fig.tight_layout()
    fig.savefig(OUT / "04_sensitivity.png", dpi=150)
    plt.close(fig)

    report.append("## 4. Sensitivity of the optimal overbooking level\n")
    report.append(f"Grid search over levels 0-30% in 2.5% steps, {cfg['sens_runs']} runs per "
                  "point. The cancellation rate is varied because it drives overbooking far "
                  "more than the no-show rate (~2% in the data). Booking requests are "
                  "scaled so that the number of non-cancelled bookings stays the same.\n")
    report.append("| Denied cost \\ cancellation factor | " + " | ".join(f"x{f}" for f in factors) + " |")
    report.append("|---:|" + "---:|" * len(factors))
    for i, c in enumerate(costs):
        report.append(f"| {c:.0f} | " + " | ".join(f"{g:.1%}" for g in grid[i]) + " |")
    report.append("\nMore cancellations push the optimal level up, higher compensation "
                  "costs push it down.\n")


# --------------------------------------------------------------------------
# 5. Convergence: how many runs do we need?
# --------------------------------------------------------------------------
def convergence(cfg, report, level):
    p = Params(n_days=cfg["days"], overbooking_level=level)
    res = run_replications(p, n_runs=cfg["conv_runs"], seed=SEED)
    runs = res["mean_profit"]["runs"]
    ns = np.arange(2, len(runs) + 1)
    means = np.array([runs[:k].mean() for k in ns])
    half = np.array([1.96 * runs[:k].std(ddof=1) / np.sqrt(k) for k in ns])

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(ns, means, label="Running mean")
    ax.fill_between(ns, means - half, means + half, alpha=0.3, label="95% CI")
    ax.set(xlabel="Number of simulation runs", ylabel="Mean profit per night",
           title=f"Convergence of the estimate (overbooking {level:.1%})")
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
    cfg = (dict(runs=4, days=90, val_runs=2, val_days=200, sens_runs=2, conv_runs=8,
                gof_days=500)
           if args.quick else
           dict(runs=20, days=180, val_runs=4, val_days=500, sens_runs=6, conv_runs=40,
                gof_days=3000))
    OUT.mkdir(exist_ok=True)

    report = ["# Analysis results\n",
              "Generated by `python analysis/run_analysis.py`"
              + (" --quick (low precision)" if args.quick else "") + ". "
              "All prices and rates are model assumptions (see `hotel_sim/params.py`).\n"]
    print("[validation]", flush=True)
    validation(cfg, report)
    print("[chi-square test]", flush=True)
    goodness_of_fit(cfg, report)
    print("[optimum and risk]", flush=True)
    rows, levels, best = optimum_and_risk(cfg, report)
    print("[textbook vs simulation]", flush=True)
    naive_vs_simulation(cfg, report, rows, levels)
    print("[sensitivity]", flush=True)
    sensitivity(cfg, report)
    print("[convergence]", flush=True)
    convergence(cfg, report, best[0.0])

    (OUT / "results.md").write_text("\n".join(report) + "\n")
    print(f"Done. See {OUT / 'results.md'} and the PNG files next to it.")


if __name__ == "__main__":
    main()
