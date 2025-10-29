import streamlit as st
from components.kpi import kpi_tile
from components.charts import bar

def render():
    st.title("DASHBOARD — Inwestor")
    insights = st.session_state["insights"]
    c1,c2,c3,c4 = st.columns(4)
    kpi_tile(c1, "ADR (avg)", float(insights["ADR"].astype(float).mean()))
    kpi_tile(c2, "RevPAR (avg)", float(insights["RevPAR"].astype(float).mean()))
    proxy = (insights["RevPAR"].astype(float).mean() - insights["var_cost_per_occ_room"].astype(float).mean())/max(insights["ADR"].astype(float).mean(),1)*100
    kpi_tile(c3, "EBITDA% (proxy)", float(proxy))
    kpi_tile(c4, "BE rooms (median)", float(insights["BE_rooms"].astype(float).median()))
    fig = bar(insights.reset_index(), x="month", y="RevPAR", title="RevPAR (mies.)")
    st.plotly_chart(fig, use_container_width=True)
    st.info("Dostęp tylko do odczytu. Raporty w zakładce RAPORTY.")
