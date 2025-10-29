import streamlit as st

def render():
    st.title("ROOMS — ceny i pickup (demo)")
    st.caption("Wersja demo bez integracji CRS/RMS.")
    insights = st.session_state["insights"]
    px_df = insights.reset_index()[["month"]].assign(
        occ=insights["occ"].values,
        ADR=insights["ADR"].values,
        RevPAR=insights["RevPAR"].values,
    )
    st.dataframe(px_df, use_container_width=True)
