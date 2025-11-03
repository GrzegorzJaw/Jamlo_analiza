# =========================================
# path: core/state_local.py
# =========================================
from __future__ import annotations

from typing import Dict, List, Tuple
import pandas as pd
import streamlit as st

# --- kolumny dzienne (PL) ---
ROOMS_DAY_COLS = [
    "pokoje_do_sprzedania",
    "pokoje_oos",
    "sprzedane_pokoje_bez",
    "sprzedane_pokoje_ze",
    "przychody_pokoje_netto",
]
FNB_REVENUE_DAY_COLS = [
    "fnb_sniadania_pakietowe",
    "fnb_kolacje_pakietowe",
    "fnb_zywnosc_a_la_carte",
    "fnb_napoje_a_la_carte",
    "fnb_zywnosc_bankiety",
    "fnb_napoje_bankiety",
    "fnb_wynajem_sali",
    "fnb_catering",
]
OTHER_REVENUE_DAY_COLS = [
    "proc_pokoi_parking",
    "przychody_parking",
    "przychody_sklep_recepcyjny",
    "przychody_pralnia_gosci",
    "przychody_transport_gosci",
    "przychody_rekreacja",
    "przychody_pozostale",
]
ROOMS_COST_PERSONNEL = [
    "r_osobowe_wynagrodzenia",
    "r_osobowe_zus",
    "r_osobowe_pfron",
    "r_osobowe_wyzywienie",
    "r_osobowe_odziez_bhp",
    "r_osobowe_medyczne",
    "r_osobowe_inne",
]
ROOMS_COST_MATERIALS = [
    "r_materialy_eksploatacyjne_spozywcze",
    "r_materialy_kosmetyki_srodki",
    "r_materialy_inne_biurowe",
]
ROOMS_COST_SERVICES = [
    "r_uslugi_sprzatania",
    "r_uslugi_pranie_zew",
    "r_uslugi_pranie_odziezy_sluzbowej",
    "r_uslugi_wynajem_sprzetu",
    "r_uslugi_inne_bhp",
]
ROOMS_COST_OTHER = ["r_pozostale_prowizje_ota_gds"]
FNB_COST_RAW = ["g_koszt_surowca_zywnosc_pln", "g_koszt_surowca_napoje_pln"]
FNB_COST_PERSONNEL = [
    "g_osobowe_wynagrodzenia",
    "g_osobowe_zus",
    "g_osobowe_pfron",
    "g_osobowe_wyzywienie",
    "g_osobowe_odziez_bhp",
    "g_osobowe_medyczne",
    "g_osobowe_inne",
]
FNB_COST_MATERIALS = [
    "g_materialy_zastawa",
    "g_materialy_drobne_wyposazenie",
    "g_materialy_bielizna_dekoracje",
    "g_materialy_karty_dan",
    "g_materialy_srodki_czystosci",
    "g_materialy_inne",
]
FNB_COST_SERVICES = [
    "g_uslugi_sprzatania_tapicerki",
    "g_uslugi_pranie_odziezy_sluzbowej",
    "g_uslugi_pranie_bielizny_gastro",
    "g_uslugi_wynajem_sprzetu_lokali",
    "g_uslugi_inne",
]
DAY_COLUMNS: List[str] = (
    ROOMS_DAY_COLS
    + FNB_REVENUE_DAY_COLS
    + OTHER_REVENUE_DAY_COLS
    + ROOMS_COST_PERSONNEL
    + ROOMS_COST_MATERIALS
    + ROOMS_COST_SERVICES
    + ROOMS_COST_OTHER
    + FNB_COST_RAW
    + FNB_COST_PERSONNEL
    + FNB_COST_MATERIALS
    + FNB_COST_SERVICES
)

# --- helpers czasu/miesięcy ---
def _month_dates(year: int, month: int) -> List[pd.Timestamp]:
    start = pd.Timestamp(year=year, month=month, day=1)
    end = (start + pd.offsets.MonthBegin(1))
    return list(pd.date_range(start, end - pd.Timedelta(days=1), freq="D"))

def _create_month_df(year: int, month: int) -> pd.DataFrame:
    df = pd.DataFrame({"data": _month_dates(year, month)})
    for c in DAY_COLUMNS:
        df[c] = 0.0
    return df

# --- stan w sesji (bez I/O zewnętrznego) ---
def _ensure_exec(year: int) -> None:
    if "exec" not in st.session_state:
        st.session_state["exec"] = {}
    if year not in st.session_state["exec"]:
        st.session_state["exec"][year] = {}
    if "exec_audit" not in st.session_state:
        st.session_state["exec_audit"] = {}
    if year not in st.session_state["exec_audit"]:
        st.session_state["exec_audit"][year] = {}

def init_exec_year(year: int) -> None:
    """Tworzy puste DF-y dla 12 miesięcy danego roku w sesji."""
    _ensure_exec(year)
    for m in range(1, 13):
        if m not in st.session_state["exec"][year]:
            st.session_state["exec"][year][m] = _create_month_df(year, m)
            st.session_state["exec_audit"][year][m] = []

def get_month_df(year: int, month: int) -> pd.DataFrame:
    _ensure_exec(year)
    return st.session_state["exec"][year][month].copy(deep=True)

def _diff_frames(before: pd.DataFrame, after: pd.DataFrame) -> pd.DataFrame:
    before = before.sort_values("data").reset_index(drop=True)
    after = after.sort_values("data").reset_index(drop=True)
    rows = []
    for col in after.columns:
        if col == "data":
            continue
        dif = before[col] != after[col]
        if dif.any():
            changed = after.loc[dif, ["data", col]].copy()
            changed["kolumna"] = col
            changed["stara_wartosc"] = before.loc[dif, col].values
            changed["nowa_wartosc"] = after.loc[dif, col].values
            rows.append(changed[["data", "kolumna", "stara_wartosc", "nowa_wartosc"]])
    if rows:
        out = pd.concat(rows, ignore_index=True)
        out["data"] = pd.to_datetime(out["data"]).dt.date
        return out
    return pd.DataFrame(columns=["data", "kolumna", "stara_wartosc", "nowa_wartosc"])

def save_month_df(year: int, month: int, edited: pd.DataFrame, user: str = "GM") -> pd.DataFrame:
    """Zapisuje zmiany do sesji i tworzy audit log (kto/co/kiedy)."""
    _ensure_exec(year)
    before = st.session_state["exec"][year][month]
    changes = _diff_frames(before, edited)
    if not changes.empty:
        audit = st.session_state["exec_audit"][year][month]
        ts = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
        for _, r in changes.iterrows():
            audit.append({
                "czas": ts,
                "kto": user,
                "data": r["data"].isoformat() if hasattr(r["data"], "isoformat") else str(r["data"]),
                "kolumna": r["kolumna"],
                "stara": float(r["stara_wartosc"]),
                "nowa": float(r["nowa_wartosc"]),
            })
        st.session_state["exec_audit"][year][month] = audit
    st.session_state["exec"][year][month] = edited.copy(deep=True)
    return changes

def get_audit(year: int, month: int) -> pd.DataFrame:
    _ensure_exec(year)
    return pd.DataFrame(st.session_state["exec_audit"][year][month])

def split_editable(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Zwraca (≤ dziś, > dziś)."""
    today = pd.Timestamp.today().normalize()
    d = df.copy()
    d["data"] = pd.to_datetime(d["data"])
    return d[d["data"] <= today].copy(), d[d["data"] > today].copy()

def missing_days(df: pd.DataFrame) -> pd.Series:
    """Heurystyka braków: brak przychodu z pokoi."""
    return df.loc[df["przychody_pokoje_netto"] <= 0.0, "data"]

# --- KPI ---
def _sum(df: pd.DataFrame, cols) -> float:
    if df.empty:
        return 0.0
    if isinstance(cols, list):
        return float(df[cols].sum().sum())
    return float(df[cols].sum())

def kpi_rooms_month(df: pd.DataFrame) -> Dict[str, float]:
    rooms_available = float((df["pokoje_do_sprzedania"] - df["pokoje_oos"]).sum())
    sold = float(df["sprzedane_pokoje_bez"].sum() + df["sprzedane_pokoje_ze"].sum())
    occ = (sold / rooms_available) if rooms_available > 0 else 0.0
    rev_rooms = float(df["przychody_pokoje_netto"].sum())
    k_all = (
        _sum(df, ROOMS_COST_PERSONNEL)
        + _sum(df, ROOMS_COST_MATERIALS)
        + _sum(df, ROOMS_COST_SERVICES)
        + _sum(df, ROOMS_COST_OTHER)
    )
    return {
        "zdolnosc": rooms_available,
        "sprzedane": sold,
        "frekwencja": float(occ),
        "revpor": float(rev_rooms / sold) if sold > 0 else 0.0,
        "sprzedaz_pokoi": rev_rooms,
        "k_wydzialowe": float(k_all),
        "wynik": float(rev_rooms - k_all),
        "koszt_na_sprzedany_pokoj": float(k_all / sold) if sold > 0 else 0.0,
    }

def kpi_rooms_ytd(exec_state: Dict[int, Dict[int, pd.DataFrame]], year: int, month: int) -> Dict[str, float]:
    frames = [exec_state[year][m] for m in range(1, month + 1)]
    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["pokoje_do_sprzedania"])
    return kpi_rooms_month(df)

def kpi_fnb_month(df: pd.DataFrame) -> Dict[str, float]:
    rev = _sum(df, FNB_REVENUE_DAY_COLS)
    k_all = (
        _sum(df, FNB_COST_RAW)
        + _sum(df, FNB_COST_PERSONNEL)
        + _sum(df, FNB_COST_MATERIALS)
        + _sum(df, FNB_COST_SERVICES)
    )
    return {
        "sprzedaz_fnb": float(rev),
        "g_koszt_surowca": float(_sum(df, FNB_COST_RAW)),
        "g_k_razem": float(k_all),
        "g_wynik": float(rev - k_all),
    }

def kpi_fnb_ytd(exec_state: Dict[int, Dict[int, pd.DataFrame]], year: int, month: int) -> Dict[str, float]:
    frames = [exec_state[year][m] for m in range(1, month + 1)]
    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["fnb_sniadania_pakietowe"])
    return kpi_fnb_month(df)

def export_all_to_excel(path: str) -> str:
    """Eksportuje wszystkie lata/miesiące z sesji do jednego XLSX (arkusze WYKONANIE_YYYY_MM)."""
    if "exec" not in st.session_state or not st.session_state["exec"]:
        raise RuntimeError("Brak danych w sesji do eksportu.")
    with pd.ExcelWriter(path, engine="openpyxl") as wr:
        for year, months in st.session_state["exec"].items():
            for m, df in months.items():
                name = f"WYKONANIE_{year}_{int(m):02d}"[:31]
                df.to_excel(wr, index=False, sheet_name=name)
    return path

