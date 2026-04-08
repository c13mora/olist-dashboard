"""
views/customers.py — Customer Analytics page content
"""

import streamlit as st
import pandas as pd

from st_theme import (
    render_header, section_header, kpi_row, chart_card, svg_icon,
    fmt_currency, fmt_pct,
    stacked_bar, histogram, line_chart,
)
from utils.data import (
    get_date_range, get_all_categories,
    build_base_filter,
    get_ltv_and_churn, get_ltv_distribution,
    get_new_repeat_customers, get_repeat_rate_trend,
)

brand = st.session_state.get("brand", {})
sym   = brand.get("brand", {}).get("currency_symbol", "$")
c     = brand.get("colors", {})

# ── Sidebar filters ───────────────────────────────────────────────────────────
with st.sidebar:
    min_date, max_date = get_date_range()

    st.markdown("##### Date Range")
    date_from = st.date_input(
        "From", value=pd.to_datetime("2017-01-01"),
        min_value=pd.to_datetime(min_date), max_value=pd.to_datetime(max_date),
        label_visibility="collapsed", key="cust_from",
    )
    date_to = st.date_input(
        "To", value=pd.to_datetime(max_date),
        min_value=pd.to_datetime(min_date), max_value=pd.to_datetime(max_date),
        label_visibility="collapsed", key="cust_to",
    )

    st.markdown("##### Category")
    selected_cats = st.multiselect(
        "Categories (all if empty)", get_all_categories(), default=[],
        label_visibility="collapsed", key="cust_cats",
    )
    st.caption("Status fixed to 'delivered' for customer metrics.")

# ── Data ──────────────────────────────────────────────────────────────────────
BASE_FILTER   = build_base_filter(date_from, date_to, ["delivered"], selected_cats)
ltv_churn     = get_ltv_and_churn(BASE_FILTER)
df_ltv        = get_ltv_distribution(BASE_FILTER)
df_new_repeat = get_new_repeat_customers(BASE_FILTER)
df_repeat_rate = get_repeat_rate_trend(BASE_FILTER)

# ── Header ────────────────────────────────────────────────────────────────────
_ctx = f"{date_from} &nbsp;→&nbsp; {date_to}"
if selected_cats:
    _ctx += f" &nbsp;·&nbsp; {len(selected_cats)} categories"
render_header(
    title="Customers",
    subtitle="Lifetime value, repeat purchase behavior, and new-vs-returning customer trends — understand who your buyers are.",
    brand=brand,
    icon="users",
    context=_ctx,
)

# ── KPI strip ─────────────────────────────────────────────────────────────────
kpi_col, _ = st.columns([2, 3])
with kpi_col:
    kpi_row([
        {"label": "Avg Customer LTV",    "value": fmt_currency(ltv_churn["avg_ltv"], sym), "delta": None, "help": "Average lifetime value per unique customer"},
        {"label": "Repeat Purchase Rate","value": fmt_pct(ltv_churn["repeat_rate"]),        "delta": None, "help": "% of customers with more than one order"},
    ])

# ── New vs Repeat ─────────────────────────────────────────────────────────────
if df_new_repeat.empty:
    section_header("New vs Repeat Customers — Monthly")
    st.info("No data for the selected filters.")
else:
    chart_card(
        "New vs Repeat Customers — Monthly",
        stacked_bar(
            df_new_repeat, x="purchase_year_month",
            series=[
                ("new_customers",    "New",    c.get("primary", "#4F8EF7")),
                ("repeat_customers", "Repeat", c.get("warning", "#F5A623")),
            ],
            x_label="Month", height=300, brand=brand,
        ),
        subtitle="Stacked by acquisition type — new vs returning customers",
    )
st.divider()

# ── LTV distribution + Repeat rate trend ──────────────────────────────────────
col_l, col_r = st.columns([3, 2], gap="large")

with col_l:
    if df_ltv.empty:
        section_header("Customer LTV Distribution", f"LTV < {sym} 2,000 (filters extreme outliers)")
        st.info("No LTV data.")
    else:
        chart_card(
            "Customer LTV Distribution",
            histogram(df_ltv, x="ltv", nbins=40, height=320, brand=brand, x_label=f"LTV ({sym})"),
            subtitle=f"LTV < {sym} 2,000 — extreme outliers excluded",
        )

with col_r:
    if df_repeat_rate.empty:
        section_header("Monthly Repeat Rate", "% of active customers with 2+ orders")
        st.info("No data.")
    else:
        chart_card(
            "Monthly Repeat Rate",
            line_chart(df_repeat_rate, x="purchase_year_month", y="repeat_rate_pct",
                       color=c.get("warning", "#F5A623"), height=320, brand=brand,
                       y_label="Repeat Rate (%)"),
            subtitle="% of active customers with 2+ orders",
        )

st.divider()
st.caption("Built with Streamlit · DuckDB · Plotly  ·  Data: Olist Brazilian E-Commerce (Kaggle)")
