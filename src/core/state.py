import pandas as pd
from core.data_io import default_frames
from utils.dates import ensure_month
from core.metrics import enrich_insights
from core.config import ProjectConfig
from core.var import monthly_var_vs_plan

def init_session(st, data_book, project_sheets=None):
    # 1) Ramy danych (domyślne lub z Excela danych)
    insights, raw, kpi = default_frames()
    if data_book.get("insights") is not None:
        insights = ensure_month(data_book["insights"])
    if data_book.get("raw") is not None:
        raw = ensure_month(data_book["raw"])
    if data_book.get("kpi") is not None:
        kpi = data_book["kpi"]

    # 2) Wzbogacenie KPI (RevPAR, BE_rooms, ...)
    insights = enrich_insights(insights)

    # 3) Session state – plan/forecast/actual
    if "plan" not in st.session_state:
        st.session_state["plan"] = insights[
            ["ADR","occ","var_cost_per_occ_room","fixed_costs","unalloc","mgmt_fees"]
        ].rename(columns={"ADR":"ADR_plan","occ":"Occ_plan"})

    if "forecast_daily" not in st.session_state:
        today = pd.Timestamp.today().normalize()
        fut = pd.date_range(today, today + pd.Timedelta(days=29), freq="D")
        st.session_state["forecast_daily"] = pd.DataFrame({
            "date":fut, "ADR_fc":300.0, "occ_fc":0.7
        })

    if "actual_daily" not in st.session_state:
        st.session_state["actual_daily"] = pd.DataFrame(
            columns=["date","sold_rooms","ADR","fnb_rev","other_rev"]
        )

    # 4) Konfiguracja projektu z Excela (Zakładki/Interakcje/Uprawnienia/Procesy)
    st.session_state["project_config"] = ProjectConfig(project_sheets or {})

    # 5) Publikacja do session + wstępny VAR m/m
    st.session_state["insights"] = insights
    st.session_state["raw"] = raw
    st.session_state["kpi"] = kpi
    st.session_state["var_mm"] = monthly_var_vs_plan(insights, st.session_state["actual_daily"])
