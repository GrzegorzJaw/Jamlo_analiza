import streamlit as st

def kpi_tile(col, label, value, delta=None):
    try:
        val = float(value)
        value_str = f"{val:,.1f}".replace(",", " ")
    except Exception:
        value_str = str(value)
    col.metric(label, value_str, delta)
