import numpy as np
import pandas as pd
import streamlit as st

def render(readonly: bool):
    st.title("WYKONANIE — dzienne inputy i VAR")
    colA, colB = st.columns(2)
    with colA:
        st.subheader("Prognozy dzienne")
        if readonly:
            st.dataframe(st.session_state["forecast_daily"], use_container_width=True)
        else:
            st.session_state["forecast_daily"] = st.data_editor(
                st.session_state["forecast_daily"], use_container_width=True, key="fc_editor"
            )
    with colB:
        st.subheader("Wykonanie dzienne")
        if readonly:
            st.dataframe(st.session_state["actual_daily"], use_container_width=True)
        else:
            st.session_state["actual_daily"] = st.data_editor(
                st.session_state["actual_daily"], num_rows="dynamic", use_container_width=True, key="act_editor"
            )
    if not st.session_state["actual_daily"].empty:
        df = st.session_state["actual_daily"].copy()
        df["month"] = pd.to_datetime(df["date"]).dt.month.map(lambda x: f"{int(x):02d}")
        agg = df.groupby("month", as_index=True).agg(
            sold=("sold_rooms","sum"),
            rooms_rev=("ADR", lambda s: np.nansum(s.values)),
        )
        agg["ADR_avg"] = agg["rooms_rev"] / agg["sold"].replace(0, np.nan)
        insights = st.session_state["insights"]
        merged = insights[["ADR","occ"]].join(agg, how="left")
        st.subheader("VAR (mies.)")
        st.dataframe(merged, use_container_width=True)
