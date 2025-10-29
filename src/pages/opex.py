import streamlit as st
def render(readonly: bool):
    st.title("OPEX — koszty niepodzielone (demo)")
    insights = st.session_state["insights"]
    base = insights.reset_index()[["month"]].assign(
        payroll=20000, energy=15000, maintenance=8000, mgmt_fee=0
    )
    st.data_editor(base, use_container_width=True, disabled=readonly)
