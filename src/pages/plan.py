import streamlit as st
from core.data_io import coerce_num
from core.var import monthly_var_vs_plan

def render(readonly: bool):
    st.title("PLAN — roczny (GM)")
    st.caption("Uproszczony plan: ADR/Occ/VarCost/Fixed/Unalloc/MgmtFees per miesiąc.")

    if readonly:
        st.warning("Tryb tylko do odczytu.")
        st.dataframe(st.session_state["plan"], use_container_width=True)
        return

    edited = st.data_editor(st.session_state["plan"], use_container_width=True, key="plan_editor")
    st.session_state["plan"] = edited

    if st.button("Opublikuj plan jako baseline", disabled=readonly):
        insights = st.session_state["insights"]
        insights.loc[edited.index, "ADR"] = coerce_num(edited["ADR_plan"])
        insights.loc[edited.index, "occ"] = coerce_num(edited["Occ_plan"])
        insights["RevPAR"] = coerce_num(insights["ADR"]) * coerce_num(insights["occ"])
        # odśwież VAR
        st.session_state["var_mm"] = monthly_var_vs_plan(insights, st.session_state["actual_daily"])
        st.success("Opublikowano plan i przeliczono VAR m/m.")
