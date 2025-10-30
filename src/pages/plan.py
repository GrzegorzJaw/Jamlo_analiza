import streamlit as st, pandas as pd
def render(readonly: bool):
    st.header("Plan")
    df: pd.DataFrame | None = st.session_state.get("plan")
    if df is None or df.empty:
        # fallback: jeśli nie zainicjalizowano planu, spróbuj z pliku Drive
        sm = st.session_state.get("sheets_map", {}); book = st.session_state.get("data_book", {})
        sheet = sm.get("PLAN", "Plan")
        src = book.get(sheet)
        if isinstance(src, pd.DataFrame): df = src.copy(); st.session_state["plan"]=df
    if df is None or df.empty:
        st.info("Brak danych planu."); return
    c1,c2 = st.columns(2)
    c1.metric("OCC (plan)", f"{df['Occ_plan'].mean()*100:.1f}%") if "Occ_plan" in df.columns else None
    c2.metric("ADR (plan)", f"{df['ADR_plan'].mean():.2f}")       if "ADR_plan" in df.columns else None
    edited = st.data_editor(df, disabled=readonly, use_container_width=True, num_rows="dynamic", key="plan_editor")
    if not readonly and st.button("Zapisz zmiany (sesja)"):
        st.session_state["plan"] = edited; st.success("Zapisano w sesji.")
