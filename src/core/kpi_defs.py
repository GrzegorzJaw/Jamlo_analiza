# Rejestr KPI + obliczenia i walidacja braków
import numpy as np
import pandas as pd

def _num(s): return pd.to_numeric(s, errors="coerce")

def _revpar(df):
    if "RevPAR" in df.columns: 
        return float(_num(df["RevPAR"]).mean()), []
    if {"ADR","occ"}.issubset(df.columns):
        return float((_num(df["ADR"])*_num(df["occ"])).mean()), []
    return None, ["ADR","occ"]

def kpi_ADR(df):
    if "ADR" in df.columns: return float(_num(df["ADR"]).mean()), []
    return None, ["ADR"]

def kpi_OCC(df):
    if "occ" in df.columns: return float(_num(df["occ"]).mean()), []
    return None, ["occ"]

def kpi_RevPAR(df):
    return _revpar(df)

def kpi_TRevPAR(df):
    # priorytet: TRevPAR kolumna; fallback: RevPAR
    if "TRevPAR" in df.columns: 
        return float(_num(df["TRevPAR"]).mean()), []
    val, missing = _revpar(df)
    return val, (["TRevPAR"] if val is None else [])

def kpi_GOP_pct(df):
    # Prostą „proxy” liczymy per miesiąc: GOP ≈ RevPAR - (var_cost_per_occ_room*occ) - fixed_costs_per_avail
    # Bez RoomsAvailable nie przeliczymy per avail – więc pokazujemy *relację* do RevPAR (proxy %).
    need = []
    rev, miss = _revpar(df); need += miss
    v = _num(df.get("var_cost_per_occ_room")) if "var_cost_per_occ_room" in df else None
    occ = _num(df.get("occ")) if "occ" in df else None
    fix = _num(df.get("fixed_costs")) if "fixed_costs" in df else None
    if rev is None or v is None or occ is None or fix is None:
        for k in ["var_cost_per_occ_room","occ","fixed_costs"]:
            if k not in df.columns: need.append(k)
        return None, need
    # Proxy: (RevPAR - (v*occ) - (fixed_costs/1e6)*alpha) / RevPAR
    # alfa malutkie, by nie „zabijać” wskaźnika bez AvailRooms; to sygnał, nie księgowość.
    alpha = 1e-6
    gop_proxy = (rev - (float(v.mean())*float(occ.mean())) - float(fix.mean())*alpha) / max(rev, 1e-9)
    return float(gop_proxy*100.0), []

def kpi_NOI(df):
    if "NOI" in df.columns: return float(_num(df["NOI"]).mean()), []
    return None, ["NOI"]

def kpi_DSCR(df):
    need=[]
    if "NOI" not in df.columns: need.append("NOI")
    if "Debt_service" not in df.columns: need.append("Debt_service")
    if need: return None, need
    noi = float(_num(df["NOI"]).mean())
    ds  = float(_num(df["Debt_service"]).mean())
    return (noi/ds if ds else None), ([] if ds else ["Debt_service"])

def kpi_LTV(df):
    need=[]
    if "Loan" not in df.columns: need.append("Loan")
    if "Asset_value" not in df.columns: need.append("Asset_value")
    if need: return None, need
    loan = float(_num(df["Loan"]).mean())
    val  = float(_num(df["Asset_value"]).mean())
    return (loan/val if val else None), ([] if val else ["Asset_value"])

def kpi_Cash(df):
    if "cash" in df.columns: return float(_num(df["cash"]).mean()), []
    return None, ["cash"]

# rejestr nazw -> funkcji
KPI_REGISTRY = {
    "ADR": kpi_ADR,
    "OCC": kpi_OCC,
    "REVPAR": kpi_RevPAR,
    "TREVPAR": kpi_TRevPAR,
    "GOP%": kpi_GOP_pct,
    "GOP %": kpi_GOP_pct,
    "NOI": kpi_NOI,
    "DSCR": kpi_DSCR,
    "LTV": kpi_LTV,
    "CASH": kpi_Cash,
}

def compute_kpis(df: pd.DataFrame, names: list[str]):
    out = []
    missing_all = set()
    for raw in names:
        name = (raw or "").strip().upper().replace("-","-").replace(" ", "")
        # mapy uproszczeń
        alias = {"GOP":"GOP%","GOPPCT":"GOP%","GOP%":"GOP%","REV-PAR":"REVPAR"}
        key = alias.get(name, name)
        # wróć do ładnej etykiety
        label = raw.strip()
        fn = KPI_REGISTRY.get(key)
        if not fn:
            out.append((label, None))
            continue
        val, missing = fn(df)
        if missing: missing_all.update(missing)
        out.append((label, val))
    return out, sorted(missing_all)
