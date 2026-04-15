# Olist E-Commerce Analytics Dashboard

**Live demo:** [olist-dashboard-bi.streamlit.app](https://olist-dashboard-bi.streamlit.app/)

**Mock Client:** Olist — a Brazilian marketplace platform connecting small merchants to major e-commerce channels.

**Scenario:** Olist's operations team needs a self-serve dashboard to monitor sales health, identify churn risk, and track customer lifetime value across their 100k+ order history. Previously this required manual SQL queries; the goal is a live dashboard any team member can use.

## Project Structure

```
olist_project/
├── data/               # Raw CSVs from Kaggle (not committed)
├── ingest.py           # Step 2: download, clean, load into DuckDB
├── dashboard.py        # Step 3: Streamlit dashboard with KPIs + charts
├── olist.duckdb        # Generated database (not committed)
└── README.md
```

## Setup

```bash
pip install kagglehub pandas duckdb streamlit plotly
```

Set your Kaggle credentials (get from kaggle.com → Account → API):
```bash
export KAGGLE_USERNAME=your_username
export KAGGLE_KEY=your_api_key
```

Then run:
```bash
python ingest.py          # Downloads data + builds DuckDB
streamlit run dashboard.py
```

## KPIs Tracked
- Monthly Revenue & Orders
- Average Order Value (AOV)
- Customer Acquisition Cost proxy (orders per customer)
- Repeat Purchase Rate (churn proxy)
- Customer Lifetime Value (LTV) by cohort
- Order Status Breakdown
- Top Product Categories by Revenue
- Delivery Performance (estimated vs actual)
