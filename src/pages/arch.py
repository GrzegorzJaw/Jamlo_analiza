# file: arch.py
import streamlit as st

def render(cfg):
    st.title("ARCH — przepływy i interakcje")

    edges = cfg.lineage_edges()
    st.subheader("Źródła ↔ Zakładki ↔ Wyjścia")
    st.dataframe(edges, width="stretch")  # szerokość elastyczna

    if cfg.interactions is not None and not cfg.interactions.empty:
        st.subheader("Interakcje (zdarzenia)")
        st.dataframe(cfg.interactions, width="stretch")

    if cfg.proc is not None and not cfg.proc.empty:
        st.subheader("Plan roczny — procesy")
        st.dataframe(cfg.proc, width="stretch")
