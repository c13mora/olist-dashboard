"""
views/overview.py — Overview page content
Called by st.navigation() in app.py. No st.set_page_config() here.
"""

import streamlit as st
import pandas as pd

from st_theme import (
    render_header, section_header, kpi_row, chart_card, svg_icon,
    fmt_currency, fmt_number, fmt_pct, pct_delta,
    dual_axis_bar_line, horizontal_bar,
)
from utils.data import (
    get_date_range, get_all_statuses,
    build_base_filter, get_prev_period,
    get_kpis, get_ltv_and_churn,
    get_monthly_revenue, get_category_breakdown,
)

# brand is injected from app.py via st.session_state
brand = st.session_state.get("brand", {})
sym   = brand.get("brand", {}).get("currency_symbol", "$")

# ── Sidebar filters ───────────────────────────────────────────────────────────
with st.sidebar:
    min_date, max_date = get_date_range()

    st.markdown("##### Date Range")
    date_from = st.date_input(
        "From", value=pd.to_datetime("2017-01-01"),
        min_value=pd.to_datetime(min_date), max_value=pd.to_datetime(max_date),
        label_visibility="collapsed", key="ov_from",
    )
    date_to = st.date_input(
        "To", value=pd.to_datetime(max_date),
        min_value=pd.to_datetime(min_date), max_value=pd.to_datetime(max_date),
        label_visibility="collapsed", key="ov_to",
    )

    st.markdown("##### Order Status")
    selected_statuses = st.multiselect(
        "Status", get_all_statuses(), default=["delivered"],
        label_visibility="collapsed", key="ov_status",
    )

# ── Data ──────────────────────────────────────────────────────────────────────
BASE_FILTER = build_base_filter(date_from, date_to, selected_statuses)
prev_from, prev_to = get_prev_period(date_from, date_to)
PREV_FILTER = build_base_filter(prev_from, prev_to, selected_statuses)

kpis      = get_kpis(BASE_FILTER)
kpis_prev = get_kpis(PREV_FILTER)
ltv       = get_ltv_and_churn(BASE_FILTER)
ltv_prev  = get_ltv_and_churn(PREV_FILTER)
df_monthly    = get_monthly_revenue(BASE_FILTER)
df_categories = get_category_breakdown(BASE_FILTER)

# ── Header ────────────────────────────────────────────────────────────────────
render_header(
    title="Executive Overview",
    subtitle="High-level snapshot of business health — revenue, orders, customer base, and top-performing categories in one view.",
    brand=brand,
    icon="layout-dashboard",
    context=f"{date_from} &nbsp;→&nbsp; {date_to} &nbsp;·&nbsp; Status: {', '.join(selected_statuses) or 'All'}",
)

# ── KPI Row ───────────────────────────────────────────────────────────────────
kpi_row([
    {"label": "Total Revenue",    "value": fmt_currency(kpis["total_revenue"], sym),               "delta": pct_delta(kpis["total_revenue"],    kpis_prev["total_revenue"]),    "help": None},
    {"label": "Orders",           "value": fmt_number(kpis["total_orders"]),                        "delta": pct_delta(kpis["total_orders"],     kpis_prev["total_orders"]),     "help": None},
    {"label": "Avg Order Value",  "value": fmt_currency(kpis["avg_order_value"], sym, decimals=2),  "delta": pct_delta(kpis["avg_order_value"],  kpis_prev["avg_order_value"]),  "help": None},
    {"label": "Unique Customers", "value": fmt_number(kpis["unique_customers"]),                    "delta": pct_delta(kpis["unique_customers"], kpis_prev["unique_customers"]), "help": None},
    {"label": "Avg LTV",          "value": fmt_currency(ltv["avg_ltv"], sym),                       "delta": pct_delta(ltv["avg_ltv"],           ltv_prev["avg_ltv"]),           "help": "Average customer lifetime value"},
    {"label": "Repeat Rate",      "value": fmt_pct(ltv["repeat_rate"]),                             "delta": pct_delta(ltv["repeat_rate"],       ltv_prev["repeat_rate"]),       "help": "% customers with >1 order"},
    {"label": "On-Time Delivery", "value": fmt_pct(kpis["on_time_pct"]),                            "delta": pct_delta(kpis["on_time_pct"],      kpis_prev["on_time_pct"]),      "help": "% orders delivered by estimated date"},
])

# ── Charts ────────────────────────────────────────────────────────────────────
col_l, col_r = st.columns([3, 2])

with col_l:
    if df_monthly.empty:
        st.info("No data for the selected filters.")
    else:
        chart_card(
            "Monthly Revenue & Orders",
            dual_axis_bar_line(df_monthly, x="purchase_year_month",
                               bar_col="revenue",  bar_label=f"Revenue ({sym})",
                               line_col="orders",  line_label="Orders",
                               height=300, brand=brand),
            subtitle="Bars = revenue (left axis)  ·  Line = orders (right axis)",
        )

with col_r:
    if df_categories.empty:
        st.info("No category data.")
    else:
        chart_card(
            "Top Categories by Revenue",
            horizontal_bar(df_categories.head(10), x="revenue", y="category",
                           x_label=f"Revenue ({sym})", y_label="Product Category",
                           height=300, brand=brand),
            subtitle=f"Top 10 by {sym} revenue",
        )

st.caption("Built with Streamlit · DuckDB · Plotly  ·  Data: Olist Brazilian E-Commerce (Kaggle)")
