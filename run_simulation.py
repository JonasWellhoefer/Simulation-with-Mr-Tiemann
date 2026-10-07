"""Run the hotel overbooking simulation and compare with exact results.

Usage: python run_simulation.py [--nights 20000] [--seed 42]
"""
import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from overbooking import analytic  # noqa: E402
from overbooking.model import HotelParams, sweep_bookings  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nights", type=int, default=20000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="results")
    args = ap.parse_args()

    params = HotelParams()
    levels = np.arange(params.capacity, params.capacity + 31)
    sim = sweep_bookings(params, levels, args.nights, args.seed)
    exact_profit = np.array([analytic.expected_profit(params, n) for n in levels])
    exact_pden = np.array([analytic.prob_denied(params, n) for n in levels])

    best_sim = int(levels[sim["mean_profit"].argmax()])
    best_exact = analytic.optimal_bookings(params)

    print(f"Parameters: {params}")
    print(f"Nights simulated per level: {args.nights}")
    print(f"{'N':>4} {'sim profit':>11} {'exact':>9} {'sim P(deny)':>12} {'exact':>7}")
    for i, n in enumerate(levels):
        if n % 3 == 0 or n in (best_sim, best_exact):
            print(f"{n:>4} {sim['mean_profit'][i]:>11.1f} {exact_profit[i]:>9.1f} "
                  f"{sim['p_denied'][i]:>12.3f} {exact_pden[i]:>7.3f}")
    print(f"\nOptimal bookings (simulation): {best_sim}")
    print(f"Optimal bookings (exact):      {best_exact}")
    print(f"Without overbooking ({params.capacity}): expected profit "
          f"{exact_profit[0]:.1f}; at optimum {analytic.expected_profit(params, best_exact):.1f}")

    out = Path(args.out)
    out.mkdir(exist_ok=True)
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    ax[0].errorbar(levels, sim["mean_profit"], yerr=1.96 * sim["se_profit"],
                   fmt="o", ms=3, label="Simulation (95% CI)")
    ax[0].plot(levels, exact_profit, "-", label="Exact (binomial)")
    ax[0].axvline(best_exact, ls="--", c="gray")
    ax[0].set(xlabel="Bookings accepted", ylabel="Expected profit per night",
              title="Profit vs. bookings")
    ax[0].legend()
    ax[1].plot(levels, sim["p_denied"], "o", ms=3, label="Simulation")
    ax[1].plot(levels, exact_pden, "-", label="Exact (binomial)")
    ax[1].set(xlabel="Bookings accepted", ylabel="P(at least one guest denied)",
              title="Risk of denied guests")
    ax[1].legend()
    fig.tight_layout()
    fig.savefig(out / "overbooking.png", dpi=150)
    print(f"Plot saved to {out / 'overbooking.png'}")


if __name__ == "__main__":
    main()
