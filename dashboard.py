import pandas as pd
import streamlit as st
from hotel_sim import Params, run_replications

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

    submitted = st.form_submit_button("Run simulation")

if submitted:
    params = Params(
        capacity=capacity,
        overbooking_level=overbooking_percent / 100,
        n_days=n_days,
        shock_cv=shock_cv,
    )

    with st.spinner("Running simulation..."):
        results = run_replications(params, n_runs=n_runs, seed=42)

        st.subheader("Simulation results")

    profit_column, occupancy_column, risk_column = st.columns(3)

    profit_column.metric(
        "Average nightly profit",
        f"{results['mean_profit']['mean']:,.2f}",
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