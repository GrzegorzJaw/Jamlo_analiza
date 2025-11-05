# core/state_local.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import streamlit as st


# ──────────────────────────────────────────────────────────────────────────────
# Dane w sesji
# ──────────────────────────────────────────────────────────────────────────────

def _ensure_state():
    if "exec" not in st.session_state:
        st.session_state["exec"] = {}       # {year: {month: DataFrame}}
    if "audit" not in st.session_state:
        st.session_state["audit"] = {}      # {year: {month: DataFrame}}


def init_exec_year(year: int) -> None:
    """Utwórz puste miesiące (1..12) w danym roku, jeśli brak."""
    _ensure_state()
    y = st.session_state["exec"].setdefault(year, {})
    for m in range(1, 13):
        if m not in y:
            y[m] = _empty_month_df(year, m)
    a = st.session_state["audit"].setdefault(year, {})
    for m in range(1, 13):
        if m not in a:
            a[m] = _empty_audit_df()


def _empty_month_df(year: int, month: int) -> pd.DataFrame:
    days = pd.date_range(f"{year}-{month:02d}-01", periods=32, freq="D")
    days = days[days.month == month]
    df = pd.DataFrame({"data": pd.to_datetime(days)})
    df = df.astype({"data": "datetime64[ns]"})
    return df


def _empty_audit_df() -> pd.DataFrame:
    return pd.DataFrame(columns=["czas", "uzytkownik", "data", "kolumna", "stara", "nowa"]).astype(
        {"czas": "datetime64[ns]", "uzytkownik": "string", "data": "datetime64[ns]", "kolumna": "string", "stara": "string", "nowa": "string"}
    )


def get_month_df(year: int, month: int) -> pd.DataFrame:
    _ensure_state()
    return st.session_state["exec"][year][month].copy()


def save_month_df(year: int, month: int, new_df: pd.DataFrame, user: str = "GM") -> pd.DataFrame:
    """Zapisz miesiąc, zwróć zmiany (do audytu)."""
    _ensure_state()
    new_df = _normalize_df(new_df)

    old = st.session_state["exec"][year][month]
    old_i = old.set_index("data")
    new_i = new_df.set_index("data")

    # align kolumn
    all_cols = sorted(set(old_i.columns) | set(new_i.columns))
    old_i = old_i.reindex(columns=all_cols)
    new_i = new_i.reindex(columns=all_cols)

    neq = (old_i.fillna(np.nan).astype(object) != new_i.fillna(np.nan).astype(object))
    changes_list = []
    ts = datetime.now()
    for d, row in neq.iterrows():
        changed_cols = row.index[row.values]
        for c in changed_cols:
            changes_list.append({
                "czas": ts,
                "uzytkownik": user,
                "data": pd.to_datetime(d),
                "kolumna": c,
                "stara": _to_str(old_i.at[d, c]),
                "nowa": _to_str(new_i.at[d, c]),
            })

    st.session_state["exec"][year][month] = new_df.reset_index(drop=True)

    if changes_list:
        delta = pd.DataFrame(changes_list)
        st.session_state["audit"][year][month] = pd.concat(
            [st.session_state["audit"][year][month], delta], ignore_index=True
        )
        return delta
    return pd.DataFrame(columns=["czas", "uzytkownik", "data", "kolumna", "stara", "nowa"])


def get_audit(year: int, month: int) -> pd.DataFrame:
    _ensure_state()
    return st.session_state["audit"][year][month].copy()


def split_editable(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Podziel na dni ≤ dziś (edycja) i > dziś (podgląd)."""
    today = pd.to_datetime(date.today())
    if "data" not in df.columns:
        return df.copy(), pd.DataFrame(columns=df.columns)
    mask = df["data"] <= today
    return df.loc[mask].reset_index(drop=True), df.loc[~mask].reset_index(drop=True)


def _normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    """Zapewnij kolumnę 'data' typu datetime i posortuj."""
    out = df.copy()
    if "data" in out.columns:
        out["data"] = pd.to_datetime(out["data"])
        out = out.sort_values("data")
    return out.reset_index(drop=True)


def _to_str(v) -> str:
    if pd.isna(v):
        return ""
    return str(v)


# ──────────────────────────────────────────────────────────────────────────────
# KPI – kompatybilne nazwy (stare i nowe)
# ──────────────────────────────────────────────────────────────────────────────

def _col(df: pd.DataFrame, *candidates: str) -> pd.Series:
    """Zwróć serię pierwszej istniejącej kolumny z listy (float, NaN→0)."""
    for c in candidates:
        if c in df.columns:
            return pd.to_numeric(df[c], errors="coerce").fillna(0.0)
    # brak kolumny → zera
    return pd.Series(0.0, index=df.index, dtype="float64")


def _sum_prefix(df: pd.DataFrame, prefixes: List[str]) -> float:
    cols = [c for c in df.columns if any(c.startswith(p) for p in prefixes)]
    if not cols:
        return 0.0
    val = pd.to_numeric(df[cols].stack(), errors="coerce").fillna(0.0).sum()
    return float(val)


# ── Pokoje (miesiąc)

def kpi_rooms_month(df: pd.DataFrame) -> Dict[str, float]:
    # dostępne: nowe (pokoje_dostepne_qty) lub stare (pokoje_do_sprzedania)
    rooms_available = float((_col(df, "pokoje_dostepne_qty", "pokoje_do_sprzedania")
                             - _col(df, "pokoje_oos_qty", "pokoje_oos")).sum())
    sold = float((_col(df, "pokoje_sprzedane_bez_qty", "sprzedane_pokoje_bez")
                  + _col(df, "pokoje_sprzedane_ze_qty", "sprzedane_pokoje_ze")).sum())
    revenue_rooms = float(_col(df, "pokoje_przychod_netto_pln", "przychody_pokoje_netto").sum())

    frekwencja = (sold / rooms_available) if rooms_available > 0 else 0.0
    revpor = (revenue_rooms / sold) if sold > 0 else 0.0

    # koszty wydziałowe (Pokoje) – nowe prefiks 'koszt_r_' lub stare 'r_'
    k_wydzialowe = _sum_prefix(df, ["koszt_r_", "r_"])
    wynik = revenue_rooms - k_wydzialowe

    return {
        "zdolnosc": rooms_available,
        "sprzedane": sold,
        "frekwencja": frekwencja,
        "revpor": revpor,
        "k_wydzialowe": k_wydzialowe,
        "wynik": wynik,
    }


def kpi_fnb_month(df: pd.DataFrame) -> Dict[str, float]:
    # sprzedaż F&B = suma kolumn zaczynających się od 'fnb_' (wyłączamy ew. pola nie-PLN jeżeli się pojawią)
    fnb_cols = [c for c in df.columns if c.startswith("fnb_")]
    sprzedaz_fnb = 0.0
    if fnb_cols:
        # bierzemy tylko numeryczne
        sprzedaz_fnb = float(pd.to_numeric(df[fnb_cols].stack(), errors="coerce").fillna(0.0).sum())

    # koszty F&B – nowe 'koszt_g_' lub stare 'g_'
    g_k_razem = _sum_prefix(df, ["koszt_g_", "g_"])
    g_wynik = sprzedaz_fnb - g_k_razem

    return {
        "sprzedaz_fnb": sprzedaz_fnb,
        "g_k_razem": g_k_razem,
        "g_wynik": g_wynik,
    }


# ── Pokoje / F&B – YTD

def kpi_rooms_ytd(exec_state: Dict, year: int, month: int) -> Dict[str, float]:
    _ensure_state()
    data = st.session_state["exec"] if not exec_state else exec_state
    total = {"zdolnosc": 0.0, "sprzedane": 0.0, "frekwencja": 0.0, "revpor": 0.0, "k_wydzialowe": 0.0, "wynik": 0.0}
    agg_available = 0.0
    agg_sold = 0.0
    agg_revenue = 0.0
    agg_koszty = 0.0

    for m in range(1, month + 1):
        df = data.get(year, {}).get(m)
        if not isinstance(df, pd.DataFrame):
            continue
        # MIESIĄC
        available = float((_col(df, "pokoje_dostepne_qty", "pokoje_do_sprzedania")
                           - _col(df, "pokoje_oos_qty", "pokoje_oos")).sum())
        sold = float((_col(df, "pokoje_sprzedane_bez_qty", "sprzedane_pokoje_bez")
                      + _col(df, "pokoje_sprzedane_ze_qty", "sprzedane_pokoje_ze")).sum())
        revenue = float(_col(df, "pokoje_przychod_netto_pln", "przychody_pokoje_netto").sum())
        k_r = _sum_prefix(df, ["koszt_r_", "r_"])
        agg_available += available
        agg_sold += sold
        agg_revenue += revenue
        agg_koszty += k_r

    total["zdolnosc"] = agg_available
    total["sprzedane"] = agg_sold
    total["frekwencja"] = (agg_sold / agg_available) if agg_available > 0 else 0.0
    total["revpor"] = (agg_revenue / agg_sold) if agg_sold > 0 else 0.0
    total["k_wydzialowe"] = agg_koszty
    total["wynik"] = agg_revenue - agg_koszty
    return total


def kpi_fnb_ytd(exec_state: Dict, year: int, month: int) -> Dict[str, float]:
    _ensure_state()
    data = st.session_state["exec"] if not exec_state else exec_state
    sprzedaz = 0.0
    koszty = 0.0
    for m in range(1, month + 1):
        df = data.get(year, {}).get(m)
        if not isinstance(df, pd.DataFrame):
            continue
        fnb_cols = [c for c in df.columns if c.startswith("fnb_")]
        if fnb_cols:
            sprzedaz += float(pd.to_numeric(df[fnb_cols].stack(), errors="coerce").fillna(0.0).sum())
        koszty += _sum_prefix(df, ["koszt_g_", "g_"])
    return {
        "sprzedaz_fnb": sprzedaz,
        "g_k_razem": koszty,
        "g_wynik": sprzedaz - koszty,
    }
