"""
views/operations.py — Delivery & Operations page content
"""

import streamlit as st
import pandas as pd

from st_theme import (
    render_header, section_header, kpi_row, chart_card, svg_icon,
    fmt_pct,
    multi_line_chart, donut_chart, line_chart,
)
from utils.data import (
    get_date_range, get_all_statuses,
    build_base_filter,
    get_kpis,
    get_delivery_performance, get_order_status_dist,
)

brand = st.session_state.get("brand", {})
c     = brand.get("colors", {})
t     = brand.get("theme", {})

# ── Sidebar filters ───────────────────────────────────────────────────────────
with st.sidebar:
    min_date, max_date = get_date_range()

    st.markdown("##### Date Range")
    date_from = st.date_input(
        "From", value=pd.to_datetime("2017-01-01"),
        min_value=pd.to_datetime(min_date), max_value=pd.to_datetime(max_date),
        label_visibility="collapsed", key="ops_from",
    )
    date_to = st.date_input(
        "To", value=pd.to_datetime(max_date),
        min_value=pd.to_datetime(min_date), max_value=pd.to_datetime(max_date),
        label_visibility="collapsed", key="ops_to",
    )

    st.markdown("##### Order Status")
    selected_statuses = st.multiselect(
        "Status (affects delivery charts)", get_all_statuses(), default=["delivered"],
        label_visibility="collapsed", key="ops_status",
    )
    st.caption("Order status donut always shows all statuses.")

# ── Data ──────────────────────────────────────────────────────────────────────
BASE_FILTER = build_base_filter(date_from, date_to, selected_statuses)
kpis        = get_kpis(BASE_FILTER)
df_delivery = get_delivery_performance(BASE_FILTER)
df_status   = get_order_status_dist(date_from, date_to)

# ── Header ────────────────────────────────────────────────────────────────────
render_header(
    title="Operations",
    subtitle="Delivery performance, on-time fulfillment rates, and order status distribution — track operational quality.",
    brand=brand,
    icon="truck",
    context=f"{date_from} &nbsp;→&nbsp; {date_to} &nbsp;·&nbsp; Status: {', '.join(selected_statuses) or 'All'}",
)

# ── KPI strip ─────────────────────────────────────────────────────────────────
kpi_col, _ = st.columns([2, 3])
with kpi_col:
    kpi_row([
        {"label": "On-Time Delivery", "value": fmt_pct(kpis["on_time_pct"]),               "delta": None, "help": "% of delivered orders received by the estimated date"},
        {"label": "Avg Delivery Days","value": f"{kpis['avg_delivery_days']:.1f} days",    "delta": None, "help": "Average actual delivery time (delivered orders only)"},
    ])

# ── Delivery performance + Status donut ───────────────────────────────────────
col_l, col_r = st.columns([3, 2], gap="large")

with col_l:
    if df_delivery.empty:
        section_header("Actual vs Estimated Delivery Days",
                       "Solid = actual  ·  Dashed = customer-promised estimate")
        st.info("No delivery data for the selected filters.")
    else:
        chart_card(
            "Actual vs Estimated Delivery Days",
            multi_line_chart(
                df_delivery, x="purchase_year_month",
                lines=[
                    ("actual_days",    "Actual days",    c.get("negative", "#E05F5F"), "solid"),
                    ("estimated_days", "Estimated days", t.get("text_muted", "#555E7A"), "dash"),
                ],
                height=340, brand=brand, y_title="Days",
            ),
            subtitle="Solid = actual  ·  Dashed = customer-promised estimate",
        )

with col_r:
    if df_status.empty:
        section_header("Order Status Mix", "All statuses · full date range")
        st.info("No data.")
    else:
        chart_card(
            "Order Status Mix",
            donut_chart(df_status, names="order_status", values="orders",
                        height=340, brand=brand),
            subtitle="All statuses · full date range",
        )

# ── On-time trend ─────────────────────────────────────────────────────────────
if df_delivery.empty:
    section_header("On-Time Delivery Rate — Monthly Trend",
                   "% of orders delivered by the estimated date")
    st.info("No data.")
else:
    chart_card(
        "On-Time Delivery Rate — Monthly Trend",
        line_chart(df_delivery, x="purchase_year_month", y="on_time_pct",
                   color=c.get("positive", "#1EC8A0"), height=260, brand=brand,
                   y_label="On-Time Rate (%)"),
        subtitle="% of orders delivered by the estimated date",
    )

st.caption("Built with Streamlit · DuckDB · Plotly  ·  Data: Olist Brazilian E-Commerce (Kaggle)")
