"""
utils/data.py — Shared data layer for all dashboard pages
==========================================================
All DuckDB connections, queries, and filter helpers live here so every page
imports from a single source of truth.

Usage:
    from utils.data import get_kpis, get_monthly_revenue, build_base_filter, ...
"""

import streamlit as st
import pandas as pd
import duckdb
from pathlib import Path
from datetime import datetime, timedelta

# ── Database path — always resolves to the project root ───────────────────────
# utils/data.py is one level below the project root, so .parent.parent = root.
DB_PATH = Path(__file__).parent.parent / "olist.duckdb"


# ─────────────────────────────────────────────────────────────────────────────
# CONNECTION
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_resource
def get_connection() -> duckdb.DuckDBPyConnection:
    """
    Singleton read-only DuckDB connection.
    Shared across all pages and reruns via st.cache_resource.

    On first run (e.g. Streamlit Cloud), if the database doesn't exist,
    the ingest pipeline runs automatically using Kaggle credentials stored
    in st.secrets (KAGGLE_USERNAME and KAGGLE_KEY).
    """
    if not DB_PATH.exists():
        import os, sys
        # Inject Kaggle credentials from Streamlit secrets into the environment
        # so ingest.py (which uses os.environ / load_dotenv) can find them.
        for key in ("KAGGLE_USERNAME", "KAGGLE_KEY"):
            if key not in os.environ and key in st.secrets:
                os.environ[key] = st.secrets[key]

        sys.path.insert(0, str(DB_PATH.parent))
        import ingest
        with st.spinner("Building database for the first time — this takes about 2 minutes..."):
            ingest.main()

    return duckdb.connect(str(DB_PATH), read_only=True)


@st.cache_data(ttl=300)
def query(sql: str) -> pd.DataFrame:
    """Execute SQL and return a DataFrame. Cached for 5 minutes."""
    return get_connection().execute(sql).df()


# ─────────────────────────────────────────────────────────────────────────────
# DATE RANGE
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def get_date_range() -> tuple[str, str]:
    """Return the min and max purchase_date in the database."""
    row = query(
        "SELECT MIN(purchase_date), MAX(purchase_date) FROM orders_enriched"
    ).iloc[0]
    return str(row.iloc[0]), str(row.iloc[1])


# ─────────────────────────────────────────────────────────────────────────────
# FILTER BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def build_base_filter(
    date_from,
    date_to,
    statuses: list[str] | None = None,
    categories: list[str] | None = None,
) -> str:
    """
    Build a SQL WHERE clause from sidebar filter values.

    - statuses: defaults to ["delivered"] when None or empty.
    - categories: no category filter when None or empty (all categories).
    """
    if not statuses:
        statuses = ["delivered"]
    status_list = ", ".join(f"'{s}'" for s in statuses)
    status_clause = f"AND order_status IN ({status_list})"

    cat_clause = ""
    if categories:
        cat_list = ", ".join(f"'{c}'" for c in categories)
        cat_clause = f"AND top_category IN ({cat_list})"

    return f"""
        WHERE purchase_date BETWEEN '{date_from}' AND '{date_to}'
        {status_clause}
        {cat_clause}
    """


def get_prev_period(date_from, date_to) -> tuple[str, str]:
    """
    Return the previous period of equal length, ending the day before date_from.
    Used for period-over-period KPI deltas on the Overview page.

    Example: 2017-01-01 → 2017-12-31  →  prev = 2016-01-02 → 2017-01-01
    """
    d_from = datetime.strptime(str(date_from), "%Y-%m-%d")
    d_to   = datetime.strptime(str(date_to),   "%Y-%m-%d")
    duration = d_to - d_from
    prev_to   = d_from - timedelta(days=1)
    prev_from = prev_to - duration
    return str(prev_from.date()), str(prev_to.date())


# ─────────────────────────────────────────────────────────────────────────────
# KPI QUERIES
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def get_kpis(base_filter: str) -> dict:
    sql = f"""
    SELECT
        ROUND(SUM(revenue), 2)                                                AS total_revenue,
        COUNT(DISTINCT order_id)                                              AS total_orders,
        ROUND(AVG(revenue), 2)                                                AS avg_order_value,
        COUNT(DISTINCT customer_unique_id)                                    AS unique_customers,
        ROUND(AVG(CASE WHEN delivery_days_actual IS NOT NULL
                       THEN delivery_days_actual END), 1)                    AS avg_delivery_days,
        ROUND(100.0 * SUM(CASE WHEN delivery_on_time THEN 1 ELSE 0 END)
              / NULLIF(COUNT(CASE WHEN delivery_days_actual IS NOT NULL
                                  THEN 1 END), 0), 1)                        AS on_time_pct
    FROM orders_enriched
    {base_filter}
    """
    return query(sql).iloc[0].to_dict()


@st.cache_data(ttl=300)
def get_ltv_and_churn(base_filter: str) -> dict:
    sql = f"""
    SELECT
        ROUND(AVG(ltv), 2)                                                    AS avg_ltv,
        ROUND(100.0 * SUM(CASE WHEN is_repeat_customer THEN 1 END)
              / NULLIF(COUNT(*), 0), 1)                                       AS repeat_rate
    FROM customer_metrics
    WHERE customer_unique_id IN (
        SELECT DISTINCT customer_unique_id
        FROM orders_enriched {base_filter}
    )
    """
    return query(sql).iloc[0].to_dict()


# ─────────────────────────────────────────────────────────────────────────────
# REVENUE QUERIES
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def get_monthly_revenue(base_filter: str) -> pd.DataFrame:
    return query(f"""
    SELECT
        purchase_year_month,
        ROUND(SUM(revenue), 2)                                                AS revenue,
        COUNT(DISTINCT order_id)                                              AS orders,
        COUNT(DISTINCT customer_unique_id)                                    AS customers,
        ROUND(SUM(revenue) / NULLIF(COUNT(DISTINCT order_id), 0), 2)         AS avg_order_value
    FROM orders_enriched
    {base_filter}
    GROUP BY 1
    ORDER BY 1
    """)


@st.cache_data(ttl=300)
def get_category_breakdown(base_filter: str) -> pd.DataFrame:
    return query(f"""
    SELECT
        top_category                                                           AS category,
        ROUND(SUM(revenue), 2)                                                AS revenue,
        COUNT(DISTINCT order_id)                                              AS orders
    FROM orders_enriched
    {base_filter}
    AND top_category IS NOT NULL
    GROUP BY 1
    ORDER BY revenue DESC
    LIMIT 15
    """)


# ─────────────────────────────────────────────────────────────────────────────
# CUSTOMER QUERIES
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def get_ltv_distribution(base_filter: str) -> pd.DataFrame:
    return query(f"""
    SELECT ltv, total_orders, customer_state
    FROM customer_metrics
    WHERE customer_unique_id IN (
        SELECT DISTINCT customer_unique_id
        FROM orders_enriched {base_filter}
    )
    AND ltv < 2000
    """)


@st.cache_data(ttl=300)
def get_new_repeat_customers(base_filter: str) -> pd.DataFrame:
    return query(f"""
    SELECT
        o.purchase_year_month,
        COUNT(DISTINCT CASE WHEN cm.total_orders = 1 THEN o.customer_unique_id END) AS new_customers,
        COUNT(DISTINCT CASE WHEN cm.total_orders > 1 THEN o.customer_unique_id END) AS repeat_customers
    FROM orders_enriched o
    JOIN customer_metrics cm USING (customer_unique_id)
    {base_filter}
    GROUP BY 1
    ORDER BY 1
    """)


@st.cache_data(ttl=300)
def get_repeat_rate_trend(base_filter: str) -> pd.DataFrame:
    """Monthly repeat customer rate (%) for trend line on Customers page."""
    return query(f"""
    SELECT
        o.purchase_year_month,
        ROUND(100.0 * COUNT(DISTINCT CASE WHEN cm.total_orders > 1 THEN o.customer_unique_id END)
              / NULLIF(COUNT(DISTINCT o.customer_unique_id), 0), 1)           AS repeat_rate_pct
    FROM orders_enriched o
    JOIN customer_metrics cm USING (customer_unique_id)
    {base_filter}
    GROUP BY 1
    ORDER BY 1
    """)


# ─────────────────────────────────────────────────────────────────────────────
# OPERATIONS QUERIES
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def get_order_status_dist(date_from, date_to) -> pd.DataFrame:
    """
    Order status distribution for the full date range (no status filter applied
    intentionally — the point is to see the mix of all statuses).
    """
    return query(f"""
    SELECT order_status, COUNT(*) AS orders
    FROM orders_enriched
    WHERE purchase_date BETWEEN '{date_from}' AND '{date_to}'
    GROUP BY 1
    ORDER BY orders DESC
    """)


@st.cache_data(ttl=300)
def get_delivery_performance(base_filter: str) -> pd.DataFrame:
    return query(f"""
    SELECT
        purchase_year_month,
        ROUND(AVG(delivery_days_actual), 1)                                   AS actual_days,
        ROUND(AVG(delivery_days_estimated), 1)                                AS estimated_days,
        ROUND(100.0 * SUM(CASE WHEN delivery_on_time THEN 1 END)
              / NULLIF(COUNT(*), 0), 1)                                       AS on_time_pct
    FROM orders_enriched
    {base_filter}
    AND delivery_days_actual IS NOT NULL
    GROUP BY 1
    ORDER BY 1
    """)


@st.cache_data(ttl=300)
def get_all_statuses() -> list[str]:
    """All distinct order statuses for the status multiselect."""
    return query(
        "SELECT DISTINCT order_status FROM orders_enriched ORDER BY 1"
    )["order_status"].tolist()


@st.cache_data(ttl=300)
def get_all_categories() -> list[str]:
    """All distinct top categories for the category multiselect."""
    return query(
        "SELECT DISTINCT top_category FROM orders_enriched "
        "WHERE top_category IS NOT NULL ORDER BY 1"
    )["top_category"].tolist()
