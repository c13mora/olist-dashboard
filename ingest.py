"""
ingest.py — Olist E-Commerce Data Pipeline
Step 2: Download from Kaggle, clean with Pandas, load into DuckDB

Usage:
    python ingest.py

Requirements:
    pip install kagglehub pandas duckdb
    export KAGGLE_USERNAME=...
    export KAGGLE_KEY=...
"""

import os
import sys
import pandas as pd
import duckdb
import kagglehub
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()  # loads KAGGLE_USERNAME and KAGGLE_KEY from .env into os.environ

DB_PATH = "olist.duckdb"
DATA_DIR = Path("data")


# ─── Download ────────────────────────────────────────────────────────────────

def download_dataset() -> Path:
    print("📦 Downloading Olist dataset from Kaggle...")
    path = kagglehub.dataset_download("olistbr/brazilian-ecommerce")
    src = Path(path)
    print(f"   ✓ Downloaded to: {src}")
    return src


# ─── Load & Clean ─────────────────────────────────────────────────────────────

def load_orders(src: Path) -> pd.DataFrame:
    df = pd.read_csv(src / "olist_orders_dataset.csv")

    # Parse timestamps
    date_cols = [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ]
    for col in date_cols:
        df[col] = pd.to_datetime(df[col], errors="coerce")

    # Drop clearly invalid rows (no purchase date or customer)
    df = df.dropna(subset=["order_purchase_timestamp", "customer_id"])

    # Derived columns
    df["purchase_date"] = df["order_purchase_timestamp"].dt.date
    df["purchase_year_month"] = df["order_purchase_timestamp"].dt.to_period("M").astype(str)
    df["delivery_days_actual"] = (
        df["order_delivered_customer_date"] - df["order_purchase_timestamp"]
    ).dt.days
    df["delivery_days_estimated"] = (
        df["order_estimated_delivery_date"] - df["order_purchase_timestamp"]
    ).dt.days
    df["delivery_on_time"] = df["delivery_days_actual"] <= df["delivery_days_estimated"]

    print(f"   ✓ orders: {len(df):,} rows")
    return df


def load_order_items(src: Path) -> pd.DataFrame:
    df = pd.read_csv(src / "olist_order_items_dataset.csv")
    df["shipping_limit_date"] = pd.to_datetime(df["shipping_limit_date"], errors="coerce")
    df["item_revenue"] = df["price"] + df["freight_value"]
    print(f"   ✓ order_items: {len(df):,} rows")
    return df


def load_customers(src: Path) -> pd.DataFrame:
    df = pd.read_csv(src / "olist_customers_dataset.csv")
    print(f"   ✓ customers: {len(df):,} rows")
    return df


def load_products(src: Path) -> pd.DataFrame:
    df = pd.read_csv(src / "olist_products_dataset.csv")
    # Clean category names
    df["product_category_name"] = (
        df["product_category_name"]
        .fillna("unknown")
        .str.replace("_", " ")
        .str.title()
    )
    print(f"   ✓ products: {len(df):,} rows")
    return df


def load_category_translation(src: Path) -> pd.DataFrame:
    df = pd.read_csv(src / "product_category_name_translation.csv")
    df["product_category_name_english"] = (
        df["product_category_name_english"]
        .str.replace("_", " ")
        .str.title()
    )
    return df


def load_order_reviews(src: Path) -> pd.DataFrame:
    df = pd.read_csv(src / "olist_order_reviews_dataset.csv")
    df["review_creation_date"] = pd.to_datetime(df["review_creation_date"], errors="coerce")
    print(f"   ✓ order_reviews: {len(df):,} rows")
    return df


def load_payments(src: Path) -> pd.DataFrame:
    df = pd.read_csv(src / "olist_order_payments_dataset.csv")
    # Keep one row per order (sum across installments)
    df = (
        df.groupby("order_id", as_index=False)
        .agg(
            payment_value=("payment_value", "sum"),
            payment_installments=("payment_installments", "max"),
            payment_type=("payment_type", "first"),
        )
    )
    print(f"   ✓ payments: {len(df):,} rows (aggregated per order)")
    return df


# ─── Build Analytical Tables ──────────────────────────────────────────────────

def build_orders_enriched(
    orders: pd.DataFrame,
    items: pd.DataFrame,
    customers: pd.DataFrame,
    payments: pd.DataFrame,
    products: pd.DataFrame,
    translations: pd.DataFrame,
) -> pd.DataFrame:
    """Main fact table: one row per order with revenue + customer + delivery info."""

    # Aggregate items to order level
    items_agg = (
        items.groupby("order_id", as_index=False)
        .agg(
            item_count=("order_item_id", "count"),
            product_revenue=("price", "sum"),
            freight_revenue=("freight_value", "sum"),
            total_item_revenue=("item_revenue", "sum"),
            first_product_id=("product_id", "first"),
            first_seller_id=("seller_id", "first"),
        )
    )

    # Join products + translations for category
    products = products.merge(translations, on="product_category_name", how="left")
    products["category_en"] = products["product_category_name_english"].fillna(
        products["product_category_name"]
    )
    items_with_cat = items.merge(
        products[["product_id", "category_en"]], on="product_id", how="left"
    )
    # Most common category per order
    top_cat = (
        items_with_cat.groupby("order_id")["category_en"]
        .agg(lambda x: x.value_counts().index[0] if len(x) > 0 else "unknown")
        .reset_index()
        .rename(columns={"category_en": "top_category"})
    )

    # Merge everything
    df = (
        orders
        .merge(customers[["customer_id", "customer_unique_id", "customer_city", "customer_state"]], on="customer_id", how="left")
        .merge(payments, on="order_id", how="left")
        .merge(items_agg, on="order_id", how="left")
        .merge(top_cat, on="order_id", how="left")
    )

    # Use payment_value as canonical revenue (includes installments, discounts)
    df["revenue"] = df["payment_value"].fillna(df["total_item_revenue"])

    # Drop orders with no revenue
    df = df[df["revenue"] > 0].copy()

    print(f"   ✓ orders_enriched: {len(df):,} rows")
    return df


def build_customer_metrics(orders_enriched: pd.DataFrame) -> pd.DataFrame:
    """One row per unique customer with LTV, order count, first/last order."""
    df = (
        orders_enriched
        .groupby("customer_unique_id", as_index=False)
        .agg(
            total_orders=("order_id", "nunique"),
            total_revenue=("revenue", "sum"),
            avg_order_value=("revenue", "mean"),
            first_order_date=("order_purchase_timestamp", "min"),
            last_order_date=("order_purchase_timestamp", "max"),
            customer_state=("customer_state", "first"),
            customer_city=("customer_city", "first"),
        )
    )
    df["is_repeat_customer"] = df["total_orders"] > 1
    df["days_as_customer"] = (
        df["last_order_date"] - df["first_order_date"]
    ).dt.days
    df["ltv"] = df["total_revenue"]  # LTV = total spend (mock scenario)
    df["first_order_month"] = pd.to_datetime(df["first_order_date"]).dt.to_period("M").astype(str)

    print(f"   ✓ customer_metrics: {len(df):,} rows")
    return df


def build_monthly_metrics(orders_enriched: pd.DataFrame) -> pd.DataFrame:
    """Monthly aggregates for time-series KPIs."""
    df = (
        orders_enriched[orders_enriched["order_status"] == "delivered"]
        .groupby("purchase_year_month", as_index=False)
        .agg(
            total_revenue=("revenue", "sum"),
            order_count=("order_id", "nunique"),
            unique_customers=("customer_unique_id", "nunique"),
            avg_order_value=("revenue", "mean"),
            avg_items_per_order=("item_count", "mean"),
        )
    )
    df = df.sort_values("purchase_year_month")
    df["revenue_mom_pct"] = df["total_revenue"].pct_change() * 100
    df["orders_mom_pct"] = df["order_count"].pct_change() * 100
    print(f"   ✓ monthly_metrics: {len(df):,} rows")
    return df


# ─── Load into DuckDB ─────────────────────────────────────────────────────────

def load_to_duckdb(tables: dict[str, pd.DataFrame], db_path: str) -> None:
    print(f"\n🦆 Loading into DuckDB: {db_path}")
    con = duckdb.connect(db_path)

    for name, df in tables.items():
        # DuckDB can't serialize Period dtype — convert to str
        for col in df.columns:
            if isinstance(df[col].dtype, pd.PeriodDtype):
                df[col] = df[col].astype(str)
        con.execute(f"DROP TABLE IF EXISTS {name}")
        con.execute(f"CREATE TABLE {name} AS SELECT * FROM df")
        count = con.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
        print(f"   ✓ {name}: {count:,} rows")

    con.close()
    size_mb = os.path.getsize(db_path) / 1024 / 1024
    print(f"\n✅ Database saved: {db_path} ({size_mb:.1f} MB)")


# ─── Validate ─────────────────────────────────────────────────────────────────

def validate(db_path: str) -> None:
    print("\n🔍 Quick validation queries:")
    con = duckdb.connect(db_path, read_only=True)

    revenue = con.execute(
        "SELECT ROUND(SUM(revenue), 2) FROM orders_enriched WHERE order_status = 'delivered'"
    ).fetchone()[0]
    print(f"   Total delivered revenue:  R$ {revenue:,.2f}")

    top_cats = con.execute(
        "SELECT top_category, COUNT(*) as orders FROM orders_enriched GROUP BY 1 ORDER BY 2 DESC LIMIT 5"
    ).fetchall()
    print("   Top 5 categories by orders:")
    for cat, cnt in top_cats:
        print(f"     {cat or 'unknown':<35} {cnt:,}")

    repeat_rate = con.execute(
        "SELECT ROUND(100.0 * SUM(CASE WHEN is_repeat_customer THEN 1 END) / COUNT(*), 2) FROM customer_metrics"
    ).fetchone()[0]
    print(f"   Repeat customer rate:     {repeat_rate}%")

    con.close()


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 55)
    print("  Olist E-Commerce — Data Ingestion Pipeline")
    print("=" * 55)

    # 1. Download
    src = download_dataset()

    # 2. Load raw tables
    print("\n📂 Loading raw CSVs...")
    orders = load_orders(src)
    items = load_order_items(src)
    customers = load_customers(src)
    payments = load_payments(src)
    products = load_products(src)
    translations = load_category_translation(src)
    reviews = load_order_reviews(src)

    # 3. Build analytical tables
    print("\n🔧 Building analytical tables...")
    orders_enriched = build_orders_enriched(
        orders, items, customers, payments, products, translations
    )
    customer_metrics = build_customer_metrics(orders_enriched)
    monthly_metrics = build_monthly_metrics(orders_enriched)

    # 4. Load into DuckDB
    tables = {
        "orders_enriched": orders_enriched,
        "customer_metrics": customer_metrics,
        "monthly_metrics": monthly_metrics,
        "order_items": items,
        "order_reviews": reviews,
    }
    load_to_duckdb(tables, DB_PATH)

    # 5. Validate
    validate(DB_PATH)

    print("\n🚀 Ready! Run the dashboard with:")
    print("   streamlit run dashboard.py")


if __name__ == "__main__":
    main()
