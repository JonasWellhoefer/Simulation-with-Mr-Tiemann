from dataclasses import replace

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from hotel_sim import Params, run_replications

DEFAULTS = Params()
SEED = 42
CURVE_STEP = 2.5        # % between overbooking levels in the comparison chart
CURVE_MAX_RUNS = 20     # cap so the comparison stays fast


def scale_noshow(params, factor):
    """Copy of params with every segment's no-show probability scaled."""
    segments = tuple(
        replace(s, noshow_prob=min(1.0, s.noshow_prob * factor))
        for s in params.segments
    )
    return replace(params, segments=segments)


@st.cache_data(show_spinner=False)
def replications(params, n_runs):
    return run_replications(params, n_runs=n_runs, seed=SEED)


@st.cache_data(show_spinner=False)
def profit_curve(params, n_runs, levels):
    """Same random numbers for every level (common random numbers), so the
    differences between levels are not just noise."""
    rows = []
    for level in levels:
        res = run_replications(
            replace(params, overbooking_level=level / 100), n_runs=n_runs, seed=SEED
        )
        lo, hi = res["mean_profit"]["ci95"]
        rows.append({
            "Overbooking (%)": level,
            "Profit": res["mean_profit"]["mean"],
            "CI low": lo,
            "CI high": hi,
            "Nights with denied rooms (%)": res["p_denied"]["mean"] * 100,
        })
    return pd.DataFrame(rows)


st.set_page_config(
    page_title="Hotel Overbooking Simulation",
    layout="wide",
)

st.title("Hotel Overbooking Simulation")
st.write("Explore how overbooking affects hotel profit and guest relocations.")
with st.sidebar.form("simulation_settings"):
    st.header("Simulation settings")

    capacity = st.number_input(
        "Number of rooms",
        min_value=1,
        max_value=1000,
        value=100,
        step=1,
    )

    overbooking_percent = st.slider(
        "Overbooking allowance (%)",
        min_value=0,
        max_value=50,
        value=10,
    )

    n_days = st.number_input(
        "Days per simulation run",
        min_value=2,
        max_value=365,
        value=180,
        step=1,
    )

    n_runs = st.number_input(
        "Number of simulation runs",
        min_value=2,
        max_value=100,
        value=10,
        step=1,
    )
    shock_cv = st.slider(
        "Shared no-show shock strength",
        min_value=0.0,
        max_value=1.0,
        value=0.0,
        step=0.1,
        help=(
            "0 disables the shared daily shock. Higher values increase "
            "variation in the factor affecting all no-show probabilities "
            "on the same arrival day."
        ),
    )

    st.header("Market assumptions")

    demand_rate = st.slider(
        "Booking requests per day",
        min_value=10.0,
        max_value=150.0,
        value=float(DEFAULTS.demand_rate),
        step=1.0,
        help="Average number of booking requests per arrival day.",
    )

    noshow_factor = st.slider(
        "No-show rate (relative to default)",
        min_value=0.5,
        max_value=2.0,
        value=1.0,
        step=0.1,
        help="Scales the no-show probability of every customer segment.",
    )

    denied_cost = st.number_input(
        "Cost per denied room",
        min_value=0.0,
        max_value=5000.0,
        value=float(DEFAULTS.denied_cost),
        step=10.0,
        help="Compensation when a guest arrives and no room is left.",
    )

    submitted = st.form_submit_button("Run simulation")

if submitted:
    params = scale_noshow(
        Params(
            capacity=capacity,
            overbooking_level=overbooking_percent / 100,
            n_days=n_days,
            shock_cv=shock_cv,
            demand_rate=demand_rate,
            denied_cost=denied_cost,
        ),
        noshow_factor,
    )

    with st.spinner("Running simulation..."):
        results = replications(params, n_runs)

    st.subheader("Simulation results")

    profit_column, occupancy_column, risk_column = st.columns(3)

    profit_low, profit_high = results["mean_profit"]["ci95"]
    profit_column.metric(
        "Average nightly profit",
        f"{results['mean_profit']['mean']:,.2f}",
        help=f"95% confidence interval: {profit_low:,.0f} to {profit_high:,.0f}",
    )

    occupancy_column.metric(
        "Average occupancy",
        f"{results['mean_occupancy']['mean']:.1%}",
    )

    risk_column.metric(
        "Nights with denied rooms",
        f"{results['p_denied']['mean']:.1%}",
    )

    st.caption(
        "Profit is shown in model currency units. "
        "Denial risk measures nights with at least one denied room, "
        "not the percentage of guests denied."
    )

    st.subheader("Profit vs. overbooking level")

    levels = tuple(np.arange(0, max(30, overbooking_percent) + 0.01, CURVE_STEP))
    curve_runs = min(n_runs, CURVE_MAX_RUNS)
    with st.spinner("Comparing overbooking levels..."):
        curve = profit_curve(params, curve_runs, levels)

    best = curve.loc[curve["Profit"].idxmax()]
    best_column, gain_column = st.columns(2)
    best_column.metric("Best overbooking level", f"{best['Overbooking (%)']:.1f}%")
    gain_column.metric(
        "Profit at best level vs. no overbooking",
        f"{best['Profit']:,.0f}",
        f"{best['Profit'] / curve['Profit'].iloc[0] - 1:+.1%}",
    )

    x = alt.X("Overbooking (%):Q")
    band = alt.Chart(curve).mark_area(opacity=0.25).encode(
        x=x, y=alt.Y("CI low:Q", title="Average nightly profit"), y2="CI high:Q"
    )
    line = alt.Chart(curve).mark_line(point=True).encode(
        x=x,
        y=alt.Y("Profit:Q", scale=alt.Scale(zero=False)),
        tooltip=list(curve.columns),
    )
    selected = alt.Chart(
        pd.DataFrame({"Overbooking (%)": [overbooking_percent]})
    ).mark_rule(strokeDash=[4, 4], color="gray").encode(x=x)
    st.altair_chart((band + line + selected).properties(title="Profit with 95% CI"))

    risk_chart = alt.Chart(curve).mark_line(point=True, color="firebrick").encode(
        x=x,
        y=alt.Y("Nights with denied rooms (%):Q"),
        tooltip=list(curve.columns),
    )
    st.altair_chart(
        (risk_chart + selected).properties(title="Risk of turning guests away")
    )

    st.caption(
        f"Each point uses {curve_runs} runs with the same random numbers. "
        "The shaded band is the 95% confidence interval, the dashed line "
        "marks the overbooking level chosen in the sidebar."
    )

    st.subheader("Results by simulation run")

    run_table = pd.DataFrame({
        "Run": range(1, n_runs + 1),
        "Average nightly profit": results["mean_profit"]["runs"],
        "Occupancy (%)": results["mean_occupancy"]["runs"] * 100,
        "Nights with denied rooms (%)": results["p_denied"]["runs"] * 100,
    })

    st.dataframe(run_table.round(2), hide_index=True)
    st.subheader("Average nightly profit by run")

    profit_chart = run_table.set_index("Run")[
        ["Average nightly profit"]
    ]

    st.bar_chart(profit_chart)

    st.caption(
        "Each bar represents one simulation run using the same settings. "
        "Differences between bars reflect simulated randomness."
    )
