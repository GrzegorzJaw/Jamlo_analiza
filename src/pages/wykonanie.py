import streamlit as st, pandas as pd
def render(readonly: bool):
    st.header("Wykonanie")
    df: pd.DataFrame | None = st.session_state.get("actual_daily")
    if df is None or df.empty:
        sm = st.session_state.get("sheets_map", {}); book = st.session_state.get("data_book", {})
        sheet = sm.get("WYKONANIE", "Wykonanie")
        src = book.get(sheet)
        if isinstance(src, pd.DataFrame): df = src.copy(); st.session_state["actual_daily"]=df
    if df is None or df.empty:
        st.info("Brak danych wykonania."); return
    c1,c2 = st.columns(2)
    if "ADR" in df.columns:  c1.metric("ADR (avg)", f"{df['ADR'].dropna().mean():.2f}")
    if "sold_rooms" in df.columns: c2.metric("Sprzedane pokoje (suma)", f"{int(df['sold_rooms'].dropna().sum())}")
    if readonly: st.dataframe(df, use_container_width=True)
    else:
        edited = st.data_editor(df, use_container_width=True, num_rows="dynamic", key="actual_editor")
        if st.button("Zapisz zmiany (sesja)"):
            st.session_state["actual_daily"] = edited; st.success("Zapisano w sesji.")
