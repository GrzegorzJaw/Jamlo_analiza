import pandas as pd
import numpy as np
from typing import Dict, Any
from utils.dates import ensure_month  # ABSOLUTE IMPORT

def coerce_num(s):
    return pd.to_numeric(s, errors="coerce")

def read_project_excel(uploaded) -> Dict[str, pd.DataFrame]:
    if uploaded is None:
        return {}
    try:
        return pd.read_excel(uploaded, sheet_name=None)
    except Exception:
        return {}

def read_data_workbook(uploaded) -> Dict[str, Any]:
    if uploaded is None:
        return {}
    try:
        sheets = pd.read_excel(uploaded, sheet_name=None)
    except Exception:
        return {}
    out = {}
    out["insights"] = next((sheets[k] for k in ["insight","insights","INSIGHT","INSIGHTS"] if k in sheets), None)
    out["raw"] = next((sheets[k] for k in ["raw_matrix","_raw_matrix","raw","RAW_MATRIX","RAW"] if k in sheets), None)
    out["kpi"] = next((sheets[k] for k in ["kpi","KPI","Kpi"] if k in sheets), None)
    out["cost"] = {name: df for name, df in sheets.items() if str(name).lower().startswith("cost")}
    return out

def default_frames():
    insights = pd.DataFrame({
        "month": [f"{i:02d}" for i in range(1,13)],
        "ADR": 300, "occ": 0.7, "var_cost_per_occ_room": 60,
        "fixed_costs": 300_000/12, "unalloc": 120_000/12, "mgmt_fees": 0
    })
    raw = pd.DataFrame({
        "month": [f"{i:02d}" for i in range(1,13)],
        "sold_rooms": 120*30*0.7/12, "ADR": 300
    })
    kpi = pd.DataFrame({"name":["RevPAR","EBITDA%"], "value":[210, 24.0]})
    return ensure_month(insights), ensure_month(raw), kpi
