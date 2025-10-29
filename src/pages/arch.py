import streamlit as st

def render(cfg):
    st.title("ARCH — przepływy i interakcje")

    edges = cfg.lineage_edges()
    st.subheader("Źródła ↔ Zakładki ↔ Wyjścia")
    st.dataframe(edges, use_container_width=True)

    if cfg.interactions is not None and not cfg.interactions.empty:
        st.subheader("Interakcje (zdarzenia)")
        st.dataframe(cfg.interactions, use_container_width=True)

    if cfg.proc is not None and not cfg.proc.empty:
        st.subheader("Plan roczny — procesy")
        st.dataframe(cfg.proc, use_container_width=True)
