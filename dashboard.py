"""
dashboard.py — Olist E-Commerce Analytics Dashboard
Usage:
    streamlit run dashboard.py
"""

import duckdb
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from pathlib import Path

from st_theme import (
    apply_theme,
    kpi_row, chart_card,
    fmt_currency, fmt_number,
    dual_axis_bar_line, horizontal_bar, stacked_bar,
    line_chart, donut_chart, histogram,
    COLORS,
)

DB_PATH = "olist.duckdb"

# ─── Page Config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Olist Analytics",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_theme()


# ─── Data Layer ───────────────────────────────────────────────────────────────

@st.cache_resource
def get_connection():
    if not Path(DB_PATH).exists():
        st.error(f"Database not found: {DB_PATH}\nRun `python ingest.py` first.")
        st.stop()
    return duckdb.connect(DB_PATH, read_only=True)


@st.cache_data(ttl=300)
def query(sql: str) -> pd.DataFrame:
    con = get_connection()
    return con.execute(sql).df()


def get_date_range() -> tuple[str, str]:
    row = query("SELECT MIN(purchase_date), MAX(purchase_date) FROM orders_enriched").iloc[0]
    return str(row[0]), str(row[1])


# ─── Sidebar Filters ──────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 📦 Olist Analytics")
    st.markdown("---")

    min_date, max_date = get_date_range()

    st.markdown("### 📅 Date Range")
    date_from = st.date_input("From", value=pd.to_datetime("2017-01-01"), min_value=pd.to_datetime(min_date), max_value=pd.to_datetime(max_date))
    date_to   = st.date_input("To",   value=pd.to_datetime(max_date),    min_value=pd.to_datetime(min_date), max_value=pd.to_datetime(max_date))

    st.markdown("### 🏷️ Order Status")
    all_statuses = query("SELECT DISTINCT order_status FROM orders_enriched ORDER BY 1")["order_status"].tolist()
    selected_statuses = st.multiselect("Include statuses", all_statuses, default=["delivered"])

    st.markdown("### 📦 Category")
    all_cats = query(
        "SELECT DISTINCT top_category FROM orders_enriched WHERE top_category IS NOT NULL ORDER BY 1"
    )["top_category"].tolist()
    selected_cats = st.multiselect("Categories (all if empty)", all_cats, default=[])

    st.markdown("---")
    st.caption(f"Source data: {min_date} → {max_date}")


# ─── Build Filter Clause ──────────────────────────────────────────────────────

status_list = ", ".join(f"'{s}'" for s in selected_statuses) if selected_statuses else "'delivered'"
cat_clause  = f"AND top_category IN ({', '.join(repr(c) for c in selected_cats)})" if selected_cats else ""

BASE_FILTER = f"""
    WHERE purchase_date BETWEEN '{date_from}' AND '{date_to}'
    AND order_status IN ({status_list})
    {cat_clause}
"""


# ─── KPI Queries ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def get_kpis(base_filter: str) -> dict:
    sql = f"""
    SELECT
        ROUND(SUM(revenue), 2)                                               AS total_revenue,
        COUNT(DISTINCT order_id)                                             AS total_orders,
        ROUND(AVG(revenue), 2)                                               AS avg_order_value,
        COUNT(DISTINCT customer_unique_id)                                   AS unique_customers,
        ROUND(AVG(CASE WHEN delivery_days_actual IS NOT NULL
                       THEN delivery_days_actual END), 1)                   AS avg_delivery_days,
        ROUND(100.0 * SUM(CASE WHEN delivery_on_time THEN 1 ELSE 0 END)
              / NULLIF(COUNT(CASE WHEN delivery_days_actual IS NOT NULL
                                  THEN 1 END), 0), 1)                       AS on_time_pct
    FROM orders_enriched
    {base_filter}
    """
    return query(sql).iloc[0].to_dict()


@st.cache_data(ttl=300)
def get_ltv_and_churn(base_filter: str) -> dict:
    sql = f"""
    SELECT ROUND(AVG(ltv), 2) AS avg_ltv,
           ROUND(100.0 * SUM(CASE WHEN is_repeat_customer THEN 1 END)
                 / COUNT(*), 1) AS repeat_rate
    FROM customer_metrics
    WHERE customer_unique_id IN (
        SELECT DISTINCT customer_unique_id FROM orders_enriched {base_filter}
    )
    """
    return query(sql).iloc[0].to_dict()


# ─── Chart Queries ────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def get_monthly_revenue(base_filter: str) -> pd.DataFrame:
    return query(f"""
    SELECT purchase_year_month,
           ROUND(SUM(revenue), 2)        AS revenue,
           COUNT(DISTINCT order_id)      AS orders,
           COUNT(DISTINCT customer_unique_id) AS customers,
           ROUND(SUM(revenue) / NULLIF(COUNT(DISTINCT order_id), 0), 2) AS avg_order_value
    FROM orders_enriched
    {base_filter}
    GROUP BY 1 ORDER BY 1
    """)


@st.cache_data(ttl=300)
def get_category_breakdown(base_filter: str) -> pd.DataFrame:
    return query(f"""
    SELECT top_category AS category,
           ROUND(SUM(revenue), 2)   AS revenue,
           COUNT(DISTINCT order_id) AS orders
    FROM orders_enriched
    {base_filter}
    AND top_category IS NOT NULL
    GROUP BY 1 ORDER BY revenue DESC
    LIMIT 15
    """)


@st.cache_data(ttl=300)
def get_order_status_dist(date_from, date_to) -> pd.DataFrame:
    return query(f"""
    SELECT order_status, COUNT(*) AS orders
    FROM orders_enriched
    WHERE purchase_date BETWEEN '{date_from}' AND '{date_to}'
    GROUP BY 1 ORDER BY orders DESC
    """)


@st.cache_data(ttl=300)
def get_delivery_performance(base_filter: str) -> pd.DataFrame:
    return query(f"""
    SELECT purchase_year_month,
           ROUND(AVG(delivery_days_actual), 1)    AS actual_days,
           ROUND(AVG(delivery_days_estimated), 1) AS estimated_days,
           ROUND(100.0 * SUM(CASE WHEN delivery_on_time THEN 1 END)
                 / COUNT(*), 1)                   AS on_time_pct
    FROM orders_enriched
    {base_filter}
    AND delivery_days_actual IS NOT NULL
    GROUP BY 1 ORDER BY 1
    """)


@st.cache_data(ttl=300)
def get_ltv_distribution(base_filter: str) -> pd.DataFrame:
    return query(f"""
    SELECT ltv, total_orders, customer_state
    FROM customer_metrics
    WHERE customer_unique_id IN (
        SELECT DISTINCT customer_unique_id FROM orders_enriched {base_filter}
    )
    AND ltv < 2000
    """)


@st.cache_data(ttl=300)
def get_new_repeat_customers(base_filter: str) -> pd.DataFrame:
    return query(f"""
    SELECT o.purchase_year_month,
           COUNT(DISTINCT CASE WHEN cm.total_orders = 1 THEN o.customer_unique_id END) AS new_customers,
           COUNT(DISTINCT CASE WHEN cm.total_orders > 1 THEN o.customer_unique_id END) AS repeat_customers
    FROM orders_enriched o
    JOIN customer_metrics cm USING (customer_unique_id)
    {base_filter}
    GROUP BY 1 ORDER BY 1
    """)


# ─── Fetch All Data ───────────────────────────────────────────────────────────

kpis          = get_kpis(BASE_FILTER)
ltv_churn     = get_ltv_and_churn(BASE_FILTER)
df_monthly    = get_monthly_revenue(BASE_FILTER)
df_categories = get_category_breakdown(BASE_FILTER)
df_status     = get_order_status_dist(date_from, date_to)
df_delivery   = get_delivery_performance(BASE_FILTER)
df_ltv        = get_ltv_distribution(BASE_FILTER)
df_new_repeat = get_new_repeat_customers(BASE_FILTER)


# ─── Header ───────────────────────────────────────────────────────────────────

st.title("📦 Olist E-Commerce Dashboard")
st.caption(f"Showing data from **{date_from}** to **{date_to}** · Status: {', '.join(selected_statuses)}")
st.divider()


# ─── KPI Row ──────────────────────────────────────────────────────────────────

kpi_row([
    ("💰 Total Revenue",    fmt_currency(kpis["total_revenue"]),                  None),
    ("🛒 Orders",           fmt_number(kpis["total_orders"]),                     None),
    ("📊 Avg Order Value",  fmt_currency(kpis["avg_order_value"],  decimals=2),   None),
    ("👥 Unique Customers", fmt_number(kpis["unique_customers"]),                 None),
    ("💎 Avg LTV",          fmt_currency(ltv_churn["avg_ltv"]),                   None),
    ("🔁 Repeat Rate",      f"{ltv_churn['repeat_rate']:.1f}%",                   "% of customers with >1 order"),
    ("🚚 On-Time Delivery", f"{kpis['on_time_pct']:.1f}%",                        "% orders delivered by estimated date"),
])

st.divider()


# ─── Row 1: Revenue Over Time + Category Breakdown ───────────────────────────

col_left, col_right = st.columns([3, 2])

with col_left:
    if df_monthly.empty:
        st.info("No data for selected filters.")
    else:
        chart_card(
            "Monthly Revenue & Orders",
            dual_axis_bar_line(
                df_monthly,
                x="purchase_year_month",
                bar_col="revenue",   bar_label="Revenue (R$)",
                line_col="orders",   line_label="Orders",
                height=320,
            ),
        )

with col_right:
    if df_categories.empty:
        st.info("No data for selected filters.")
    else:
        chart_card(
            "Top Categories by Revenue",
            horizontal_bar(
                df_categories.head(10),
                x="revenue",
                y="category",
                height=320,
            ),
        )

st.divider()


# ─── Row 2: Delivery Performance + Order Status + LTV Distribution ───────────

col_a, col_b, col_c = st.columns(3)

with col_a:
    if df_delivery.empty:
        st.info("No delivery data for this range.")
    else:
        # Two-line chart — built manually to keep dashed style for estimated
        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(
            x=df_delivery["purchase_year_month"],
            y=df_delivery["actual_days"],
            name="Actual days",
            mode="lines+markers",
            line=dict(color=COLORS["accent_red"], width=2),
            marker=dict(size=5),
        ))
        fig3.add_trace(go.Scatter(
            x=df_delivery["purchase_year_month"],
            y=df_delivery["estimated_days"],
            name="Estimated days",
            mode="lines",
            line=dict(color=COLORS["text_muted"], dash="dash", width=1.5),
        ))
        from st_theme import plotly_layout
        _layout = plotly_layout(height=280)
        _layout["yaxis"]["title"] = "Days"
        fig3.update_layout(**_layout)
        chart_card("Delivery: Actual vs Estimated", fig3)

with col_b:
    if df_status.empty:
        st.info("No data.")
    else:
        chart_card(
            "Order Status Mix",
            donut_chart(df_status, names="order_status", values="orders", height=280),
        )

with col_c:
    if df_ltv.empty:
        st.info("No data.")
    else:
        chart_card(
            "Customer LTV Distribution",
            histogram(df_ltv, x="ltv", nbins=40, height=280),
        )

st.divider()


# ─── Row 3: New vs Repeat Customers + AOV Trend ───────────────────────────────

col_x, col_y = st.columns(2)

with col_x:
    if df_new_repeat.empty:
        st.info("No data.")
    else:
        chart_card(
            "New vs Repeat Customers — Monthly",
            stacked_bar(
                df_new_repeat,
                x="purchase_year_month",
                series=[
                    ("new_customers",    "New",    COLORS["accent_blue"]),
                    ("repeat_customers", "Repeat", COLORS["accent_amber"]),
                ],
                height=280,
            ),
        )

with col_y:
    if df_monthly.empty:
        st.info("No data.")
    else:
        chart_card(
            "Average Order Value — Monthly Trend",
            line_chart(
                df_monthly,
                x="purchase_year_month",
                y="avg_order_value",
                height=280,
            ),
        )

st.divider()


# ─── Raw Data Explorer ────────────────────────────────────────────────────────

with st.expander("🔎 Raw Data Explorer"):
    table = st.selectbox("Table", ["orders_enriched", "customer_metrics", "monthly_metrics"])
    limit = st.slider("Rows", 10, 500, 50)
    st.dataframe(query(f"SELECT * FROM {table} LIMIT {limit}"), use_container_width=True)

st.caption("Built with Streamlit · DuckDB · Plotly · Data: Olist Brazilian E-Commerce (Kaggle)")
