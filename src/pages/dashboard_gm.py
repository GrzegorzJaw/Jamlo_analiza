import streamlit as st
from components.kpi import kpi_tile
from components.charts import line
from typing import Any


def render(project_cfg: Any = None, readonly: bool = False, **_):
    st.title("DASHBOARD — GM")
    insights = st.session_state["insights"]
    c1,c2,c3,c4 = st.columns(4)
    kpi_tile(c1, "ADR (avg)", float(insights["ADR"].astype(float).mean()))
    kpi_tile(c2, "RevPAR (avg)", float(insights["RevPAR"].astype(float).mean()))
    kpi_tile(c3, "BE rooms (median)", float(insights["BE_rooms"].astype(float).median()))
    kpi_tile(c4, "Plan rows", len(st.session_state["plan"]))
    fig = line(insights.reset_index(), x="month", ys=["ADR","RevPAR"], title="ADR & RevPAR (plan baseline)")
    st.plotly_chart(fig, use_container_width=True)
