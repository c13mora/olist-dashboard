"""
debug_sidebar.py — Run this to isolate the sidebar issue.
    streamlit run debug_sidebar.py
"""
import streamlit as st

st.set_page_config(layout="wide", initial_sidebar_state="expanded")

with st.sidebar:
    st.markdown("### Sidebar works!")
    st.selectbox("Test filter", ["A", "B", "C"])

st.title("Main content")
st.write("If you see the sidebar on the left, the issue is in our CSS or navigation setup.")
st.write("If you do NOT see the sidebar, the issue is environmental (browser state, Streamlit version quirk).")
