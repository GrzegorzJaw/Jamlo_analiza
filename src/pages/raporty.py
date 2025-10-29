import streamlit as st

def render():
    st.title("RAPORTY — Board Pack (skrót)")
    insights = st.session_state["insights"]
    rep = insights.reset_index()[["month","ADR","occ","RevPAR","BE_rooms"]]
    st.dataframe(rep, use_container_width=True)
    csv = rep.to_csv(index=False).encode("utf-8")
    st.download_button("Pobierz CSV", csv, file_name="raport_skrót.csv", mime="text/csv")
