"""Quick demo: effect of overbooking level and of correlated no-shows."""
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hotel_sim import Params, run_replications

base = Params()
print(f"{'overbook':>8} {'shock_cv':>8} {'profit/night':>13} {'occupancy':>10} "
      f"{'denied/night':>13} {'P(denied)':>10} {'CVaR5':>8}")
for shock in (0.0, 0.3):
    for level in (0.0, 0.05, 0.10, 0.15, 0.20):
        r = run_replications(replace(base, overbooking_level=level, shock_cv=shock),
                             n_runs=10, seed=1)
        print(f"{level:>8.2f} {shock:>8.1f} {r['mean_profit']['mean']:>13.0f} "
              f"{r['mean_occupancy']['mean']:>10.3f} {r['mean_denied']['mean']:>13.2f} "
              f"{r['p_denied']['mean']:>10.3f} {r['cvar_5']:>8.0f}")
