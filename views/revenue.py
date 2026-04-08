"""
views/revenue.py — Revenue & Orders page content
"""

import streamlit as st
import pandas as pd

from st_theme import (
    render_header, section_header, kpi_row, chart_card, svg_icon,
    fmt_currency, fmt_number,
    dual_axis_bar_line, horizontal_bar, line_chart,
)
from utils.data import (
    get_date_range, get_all_statuses, get_all_categories,
    build_base_filter,
    get_kpis, get_monthly_revenue, get_category_breakdown,
)

brand = st.session_state.get("brand", {})
sym   = brand.get("brand", {}).get("currency_symbol", "$")

# ── Sidebar filters ───────────────────────────────────────────────────────────
with st.sidebar:
    min_date, max_date = get_date_range()

    st.markdown("##### Date Range")
    date_from = st.date_input(
        "From", value=pd.to_datetime("2017-01-01"),
        min_value=pd.to_datetime(min_date), max_value=pd.to_datetime(max_date),
        label_visibility="collapsed", key="rev_from",
    )
    date_to = st.date_input(
        "To", value=pd.to_datetime(max_date),
        min_value=pd.to_datetime(min_date), max_value=pd.to_datetime(max_date),
        label_visibility="collapsed", key="rev_to",
    )

    st.markdown("##### Order Status")
    selected_statuses = st.multiselect(
        "Status", get_all_statuses(), default=["delivered"],
        label_visibility="collapsed", key="rev_status",
    )

    st.markdown("##### Category")
    selected_cats = st.multiselect(
        "Categories (all if empty)", get_all_categories(), default=[],
        label_visibility="collapsed", key="rev_cats",
    )

# ── Data ──────────────────────────────────────────────────────────────────────
BASE_FILTER = build_base_filter(date_from, date_to, selected_statuses, selected_cats)

kpis          = get_kpis(BASE_FILTER)
df_monthly    = get_monthly_revenue(BASE_FILTER)
df_categories = get_category_breakdown(BASE_FILTER)

# ── Header ────────────────────────────────────────────────────────────────────
_ctx = f"{date_from} &nbsp;→&nbsp; {date_to} &nbsp;·&nbsp; Status: {', '.join(selected_statuses) or 'All'}"
if selected_cats:
    _ctx += f" &nbsp;·&nbsp; {len(selected_cats)} categories"
render_header(
    title="Revenue &amp; Orders",
    subtitle="Detailed breakdown of revenue trends, average order value, and category performance over time.",
    brand=brand,
    icon="trending-up",
    context=_ctx,
)

# ── KPI strip ─────────────────────────────────────────────────────────────────
kpi_row([
    {"label": "Total Revenue",   "value": fmt_currency(kpis["total_revenue"],  sym),              "delta": None, "help": None},
    {"label": "Orders",          "value": fmt_number(kpis["total_orders"]),                        "delta": None, "help": None},
    {"label": "Avg Order Value", "value": fmt_currency(kpis["avg_order_value"], sym, decimals=2),  "delta": None, "help": None},
    {"label": "Customers",       "value": fmt_number(kpis["unique_customers"]),                    "delta": None, "help": None},
])

# ── Revenue trend ─────────────────────────────────────────────────────────────
if df_monthly.empty:
    section_header("Monthly Revenue & Orders")
    st.info("No data for the selected filters.")
else:
    chart_card(
        "Monthly Revenue & Orders",
        dual_axis_bar_line(df_monthly, x="purchase_year_month",
                           bar_col="revenue", bar_label=f"Revenue ({sym})",
                           line_col="orders", line_label="Orders",
                           height=340, brand=brand),
        subtitle="Bars = revenue (left axis)  ·  Line = orders (right axis)",
    )

# ── Categories + AOV ──────────────────────────────────────────────────────────
col_l, col_r = st.columns([3, 2])

with col_l:
    if df_categories.empty:
        section_header("Top Categories by Revenue", "Top 15 — sorted by total revenue")
        st.info("No category data.")
    else:
        chart_card(
            "Top Categories by Revenue",
            horizontal_bar(df_categories.head(15), x="revenue", y="category",
                           x_label=f"Revenue ({sym})", y_label="Product Category",
                           height=420, brand=brand),
            subtitle="Top 15 — sorted by total revenue",
        )

with col_r:
    if df_monthly.empty:
        section_header("Average Order Value — Monthly", f"Trend in {sym}")
        st.info("No data.")
    else:
        chart_card(
            "Average Order Value — Monthly",
            line_chart(df_monthly, x="purchase_year_month", y="avg_order_value",
                       height=420, brand=brand, y_label=f"AOV ({sym})"),
            subtitle=f"Trend in {sym}",
        )

st.caption("Built with Streamlit · DuckDB · Plotly  ·  Data: Olist Brazilian E-Commerce (Kaggle)")
