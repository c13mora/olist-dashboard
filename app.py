"""
app.py — Dashboard entry point (Streamlit Cloud)
=================================================
Uses st.navigation() (Streamlit 1.36+) for multi-page routing.
All shared setup (page config, theme, brand header) lives here once.
Page content lives in views/*.py.

Run:
    streamlit run app.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st

from st_theme import load_brand, apply_theme, hide_chrome, sidebar_header

# ── Brand & theme ─────────────────────────────────────────────────────────────
brand = load_brand()
st.session_state["brand"] = brand          # shared with all view modules

st.set_page_config(
    page_title=brand["brand"]["name"],
    page_icon=":material/analytics:",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_theme(brand)
hide_chrome()

# ── Logo (renders in sidebar top, handles collapsed state automatically) ───────
st.logo("assets/logo.png", size="large")

# ── Navigation ────────────────────────────────────────────────────────────────
pg = st.navigation([
    st.Page("views/overview.py",   title="Overview",         icon=":material/dashboard:"),
    st.Page("views/revenue.py",    title="Revenue & Orders", icon=":material/trending_up:"),
    st.Page("views/customers.py",  title="Customers",        icon=":material/group:"),
    st.Page("views/operations.py", title="Operations",       icon=":material/local_shipping:"),
])

pg.run()
