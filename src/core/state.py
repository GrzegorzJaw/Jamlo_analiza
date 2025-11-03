# =========================
# file: state.py
# =========================
import os
from datetime import date, timedelta
from typing import Dict, List

import pandas as pd

# ZOSTAJE: inicjalizacja projektu/insights (dotychczasowa logika)
from core.data_io import default_frames
from utils.dates import ensure_month
from core.metrics import enrich_insights
from core.config import ProjectConfig
from core.var import monthly_var_vs_plan


# ---------- NOWOŚCI: model dzienny (po polsku) ----------

# Pokoje – sprzedaż/parametry (dziennie)
ROOMS_DAY_COLS = [
    "pokoje_do_sprzedania",
    "pokoje_oos",
    "sprzedane_pokoje_bez",
    "sprzedane_pokoje_ze",
    "przychody_pokoje_netto",
]

# Gastronomia – sprzedaż (dziennie)
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

# Inne centra – przychody (dziennie)
OTHER_REVENUE_DAY_COLS = [
    "proc_pokoi_parking",
    "przychody_parking",
    "przychody_sklep_recepcyjny",
    "przychody_pralnia_gosci",
    "przychody_transport_gosci",
    "przychody_rekreacja",
    "przychody_pozostale",
]

# Pokoje – koszty (dziennie)
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

# Gastronomia – koszty (skrót; można rozszerzać)
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


def _month_dates(year: int, month: int) -> List[pd.Timestamp]:
    start = pd.Timestamp(year=year, month=month, day=1)
    end = (start + pd.offsets.MonthBegin(1))
    days = pd.date_range(start, end - pd.Timedelta(days=1), freq="D")
    return list(days)


def _create_month_df(year: int, month: int) -> pd.DataFrame:
    """Pusta tabela dni × metryki (0.0)."""
    df = pd.DataFrame({"data": _month_dates(year, month)})
    for c in DAY_COLUMNS:
        df[c] = 0.0
    return df


def _ensure_exec(year: int) -> None:
    import streamlit as st

    if "exec" not in st.session_state:
        st.session_state["exec"] = {}
    if year not in st.session_state["exec"]:
        st.session_state["exec"][year] = {}
    if "exec_snap" not in st.session_state:
        st.session_state["exec_snap"] = {}
    if year not in st.session_state["exec_snap"]:
        st.session_state["exec_snap"][year] = {}
    if "exec_audit" not in st.session_state:
        st.session_state["exec_audit"] = {}
    if year not in st.session_state["exec_audit"]:
        st.session_state["exec_audit"][year] = {}


def init_exec_year(year: int) -> None:
    """Tworzy 12 miesięcy + snapshot + audit log dla danego roku."""
    import streamlit as st

    _ensure_exec(year)
    for m in range(1, 13):
        if m not in st.session_state["exec"][year]:
            df = _create_month_df(year, m)
            st.session_state["exec"][year][m] = df
            st.session_state["exec_snap"][year][m] = df.copy(deep=True)
            st.session_state["exec_audit"][year][m] = []  # lista eventów zmian


def get_month_df(year: int, month: int) -> pd.DataFrame:
    import streamlit as st

    _ensure_exec(year)
    return st.session_state["exec"][year][month].copy(deep=True)


def _save_csv(year: int, month: int, df: pd.DataFrame) -> None:
    outdir = "/mnt/data/hotel_exec"
    os.makedirs(outdir, exist_ok=True)
    df.to_csv(os.path.join(outdir, f"{year}_{month:02d}.csv"), index=False)


def _diff_frames(before: pd.DataFrame, after: pd.DataFrame) -> pd.DataFrame:
    """Long-DF: data, kolumna, stara_wartosc, nowa_wartosc (tylko zmiany)."""
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
    return (
        pd.concat(rows, ignore_index=True)
        if rows
        else pd.DataFrame(columns=["data", "kolumna", "stara_wartosc", "nowa_wartosc"])
    )


def save_month_df(year: int, month: int, edited: pd.DataFrame, user: str = "GM") -> pd.DataFrame:
    """
    Zapisz miesiąc, zapisz CSV, zrób audit log, zwróć ramkę zmian z tego zapisu.
    Dlaczego: śledzimy kto/ kiedy/ co zmienił (compliance).
    """
    import streamlit as st

    _ensure_exec(year)
    before = st.session_state["exec"][year][month]
    changes = _diff_frames(before, edited)

    if not changes.empty:
        audit = st.session_state["exec_audit"][year][month]
        ts = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
        for _, r in changes.iterrows():
            audit.append(
                {
                    "czas": ts,
                    "kto": user,
                    "data": pd.to_datetime(r["data"]).date().isoformat(),
                    "kolumna": r["kolumna"],
                    "stara": float(r["stara_wartosc"]),
                    "nowa": float(r["nowa_wartosc"]),
                }
            )
        st.session_state["exec_audit"][year][month] = audit

    st.session_state["exec"][year][month] = edited.copy(deep=True)
    st.session_state["exec_snap"][year][month] = edited.copy(deep=True)
    _save_csv(year, month, edited)
    return changes


def get_audit(year: int, month: int) -> pd.DataFrame:
    import streamlit as st

    _ensure_exec(year)
    return pd.DataFrame(st.session_state["exec_audit"][year][month])


def split_editable(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """<= dziś (edytowalne) | > dziś (readonly)."""
    today = pd.Timestamp.today().normalize()
    d = df.copy()
    d["data"] = pd.to_datetime(d["data"])
    return d[d["data"] <= today].copy(), d[d["data"] > today].copy()


def missing_days(df: pd.DataFrame) -> pd.Series:
    """Dni bez danych – gdy brak przychodu z pokoi."""
    return df.loc[df["przychody_pokoje_netto"] <= 0.0, "data"]


# ---------- ISTNIEJĄCE: inicjalizacja aplikacji (plan/kpi) ----------

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
            ["ADR", "occ", "var_cost_per_occ_room", "fixed_costs", "unalloc", "mgmt_fees"]
        ].rename(columns={"ADR": "ADR_plan", "occ": "Occ_plan"})

    if "forecast_daily" not in st.session_state:
        today = pd.Timestamp.today().normalize()
        fut = pd.date_range(today, today + pd.Timedelta(days=29), freq="D")
        st.session_state["forecast_daily"] = pd.DataFrame({"date": fut, "ADR_fc": 300.0, "occ_fc": 0.7})

    if "actual_daily" not in st.session_state:
        st.session_state["actual_daily"] = pd.DataFrame(columns=["date", "sold_rooms", "ADR", "fnb_rev", "other_rev"])

    # 4) Konfiguracja projektu z Excela (Zakładki/Interakcje/Uprawnienia/Procesy)
    st.session_state["project_config"] = ProjectConfig(project_sheets or {})

    # 5) Publikacja do session + wstępny VAR m/m
    st.session_state["insights"] = insights
    st.session_state["raw"] = raw
    st.session_state["kpi"] = kpi
    st.session_state["var_mm"] = monthly_var_vs_plan(insights, st.session_state["actual_daily"])