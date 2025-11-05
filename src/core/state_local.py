# src/core/state_local.py
from __future__ import annotations

from datetime import date, datetime
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import streamlit as st

# ──────────────────────────────────────────────────────────────────────────────
# 1) Nowy, docelowy schemat nazw (spójne prefiksy + sufiksy)
# ──────────────────────────────────────────────────────────────────────────────

# Stare -> Nowe (komplet mapowań używanych dotąd)
OLD2NEW: Dict[str, str] = {
    # POKOJE (przychody/ilości)
    "pokoje_do_sprzedania": "pokoje_dostepne_qty",
    "pokoje_oos": "pokoje_oos_qty",
    "sprzedane_pokoje_bez": "pokoje_sprzedane_bez_qty",
    "sprzedane_pokoje_ze": "pokoje_sprzedane_ze_qty",
    "przychody_pokoje_netto": "pokoje_przychod_netto_pln",
    # F&B – przychody
    "fnb_sniadania_pakietowe": "fnb_sniadania_pakietowe_pln",
    "fnb_kolacje_pakietowe": "fnb_kolacje_pakietowe_pln",
    "fnb_zywnosc_a_la_carte": "fnb_zywnosc_a_la_carte_pln",
    "fnb_napoje_a_la_carte": "fnb_napoje_a_la_carte_pln",
    "fnb_zywnosc_bankiety": "fnb_zywnosc_bankiety_pln",
    "fnb_napoje_bankiety": "fnb_napoje_bankiety_pln",
    "fnb_catering": "fnb_catering_pln",
    "fnb_wynajem_sali": "sprzedaz_wynajem_sali_pln",
    # Inne centra – przychody
    "proc_pokoi_parking": "inne_proc_pokoi_parking_pct",
    "przychody_parking": "inne_parking_przychod_pln",
    "przychody_sklep_recepcyjny": "inne_sklep_recepcja_przychod_pln",
    "przychody_pralnia_gosci": "inne_pralnia_gosci_przychod_pln",
    "przychody_transport_gosci": "inne_transport_przychod_pln",
    "przychody_rekreacja": "inne_rekreacja_przychod_pln",
    "przychody_pozostale": "inne_pozostale_przychod_pln",
    # KOSZTY – Pokoje (prefiks r_ -> koszt_r_)
    "r_osobowe_wynagrodzenia": "koszt_r_osobowe_wynagrodzenia_pln",
    "r_osobowe_zus": "koszt_r_osobowe_zus_pln",
    "r_osobowe_pfron": "koszt_r_osobowe_pfron_pln",
    "r_osobowe_wyzywienie": "koszt_r_osobowe_wyzywienie_pln",
    "r_osobowe_odziez_bhp": "koszt_r_osobowe_odziez_bhp_pln",
    "r_osobowe_medyczne": "koszt_r_osobowe_medyczne_pln",
    "r_osobowe_inne": "koszt_r_osobowe_inne_pln",
    "r_materialy_eksploatacyjne_spozywcze": "koszt_r_materialy_eksplo_spozywcze_pln",
    "r_materialy_kosmetyki_srodki": "koszt_r_materialy_kosmetyki_czystosc_pln",
    "r_materialy_inne_biurowe": "koszt_r_materialy_inne_biurowe_pln",
    "r_uslugi_sprzatania": "koszt_r_uslugi_sprzatanie_pln",
    "r_uslugi_pranie_zew": "koszt_r_uslugi_pranie_zew_pln",
    "r_uslugi_pranie_odziezy_sluzbowej": "koszt_r_uslugi_pranie_odziezy_pln",
    "r_uslugi_wynajem_sprzetu": "koszt_r_uslugi_wynajem_sprzetu_pln",
    "r_uslugi_inne_bhp": "koszt_r_uslugi_inne_pln",
    "r_pozostale_prowizje_ota_gds": "koszt_r_prowizje_ota_gds_pln",
    # KOSZTY – F&B (prefiks g_ -> koszt_g_)
    "g_koszt_surowca_zywnosc_pln": "koszt_g_surowiec_zywnosc_pln",
    "g_koszt_surowca_napoje_pln": "koszt_g_surowiec_napoje_pln",
    "g_osobowe_wynagrodzenia": "koszt_g_osobowe_wynagrodzenia_pln",
    "g_osobowe_zus": "koszt_g_osobowe_zus_pln",
    "g_osobowe_pfron": "koszt_g_osobowe_pfron_pln",
    "g_osobowe_wyzywienie": "koszt_g_osobowe_wyzywienie_pln",
    "g_osobowe_odziez_bhp": "koszt_g_osobowe_odziez_bhp_pln",
    "g_osobowe_medyczne": "koszt_g_osobowe_medyczne_pln",
    "g_osobowe_inne": "koszt_g_osobowe_inne_pln",
    "g_materialy_zastawa": "koszt_g_materialy_zastawa_pln",
    "g_materialy_drobne_wyposazenie": "koszt_g_materialy_drobne_wypos_pln",
    "g_materialy_bielizna_dekoracje": "koszt_g_materialy_bielizna_dekor_pln",
    "g_materialy_karty_dan": "koszt_g_materialy_karty_dan_pln",
    "g_materialy_srodki_czystosci": "koszt_g_materialy_srodki_czystosci_pln",
    "g_materialy_inne": "koszt_g_materialy_inne_pln",
    "g_uslugi_sprzatania_tapicerki": "koszt_g_uslugi_sprzatanie_pln",
    "g_uslugi_pranie_odziezy_sluzbowej": "koszt_g_uslugi_pranie_odziezy_pln",
    "g_uslugi_pranie_bielizny_gastro": "koszt_g_uslugi_pranie_bielizny_pln",
    "g_uslugi_wynajem_sprzetu_lokali": "koszt_g_uslugi_wynajem_sprzetu_pln",
    "g_uslugi_inne": "koszt_g_uslugi_inne_pln",
}

# Pełen zbiór nowych nazw (przydaje się do uzupełniania braków)
NEW_SCHEMA_COLS: List[str] = sorted(set(OLD2NEW.values())) + [
    # nowo-nowe, które nie mają odpowiednika w OLD (gdyby były dodawane później)
    "pokoje_dostepne_qty",
    "pokoje_oos_qty",
    "pokoje_sprzedane_bez_qty",
    "pokoje_sprzedane_ze_qty",
    "pokoje_przychod_netto_pln",
]

# ──────────────────────────────────────────────────────────────────────────────
# 2) Warstwa danych w sesji + migracja do nowego schematu
# ──────────────────────────────────────────────────────────────────────────────

def _ensure_state() -> None:
    if "exec" not in st.session_state:
        st.session_state["exec"] = {}       # {rok: {miesiac: DataFrame}}
    if "audit" not in st.session_state:
        st.session_state["audit"] = {}      # {rok: {miesiac: DataFrame}}


def init_exec_year(year: int) -> None:
    """Tworzy puste miesiące 1..12; zapewnia nowy schemat."""
    _ensure_state()
    y = st.session_state["exec"].setdefault(year, {})
    for m in range(1, 13):
        if m not in y:
            y[m] = _new_empty_month_df(year, m)
        else:
            y[m] = apply_new_schema(y[m])  # doprowadź istniejące do schematu

    a = st.session_state["audit"].setdefault(year, {})
    for m in range(1, 13):
        if m not in a:
            a[m] = _empty_audit_df()
        else:
            a[m] = _normalize_audit(a[m])


def _new_empty_month_df(year: int, month: int) -> pd.DataFrame:
    days = pd.date_range(f"{year}-{month:02d}-01", periods=32, freq="D")
    days = days[days.month == month]
    df = pd.DataFrame({"data": pd.to_datetime(days)})
    for c in NEW_SCHEMA_COLS:
        if c not in df.columns:
            df[c] = np.nan
    df = df.astype({"data": "datetime64[ns]"})
    return df


def _empty_audit_df() -> pd.DataFrame:
    cols = ["czas", "uzytkownik", "data", "kolumna", "stara", "nowa"]
    dtypes = {
        "czas": "datetime64[ns]",
        "uzytkownik": "string",
        "data": "datetime64[ns]",
        "kolumna": "string",
        "stara": "string",
        "nowa": "string",
    }
    return pd.DataFrame(columns=cols).astype(dtypes)


def _normalize_audit(df: pd.DataFrame) -> pd.DataFrame:
    cols = {"czas": "datetime64[ns]", "uzytkownik": "string", "data": "datetime64[ns]",
            "kolumna": "string", "stara": "string", "nowa": "string"}
    out = df.copy()
    for c, t in cols.items():
        if c in out.columns:
            try:
                out[c] = out[c].astype(t)
            except Exception:
                pass
    return out


def apply_new_schema(df: pd.DataFrame) -> pd.DataFrame:
    """
    Migruje DataFrame do nowych nazw:
    - rename starych -> nowe,
    - dopisuje brakujące nowe kolumny (NaN),
    - nie usuwa kolumn ponad schemat (żeby nic nie zginęło).
    """
    if df is None or df.empty:
        return df
    out = df.copy()
    # rename
    ren = {old: new for old, new in OLD2NEW.items() if old in out.columns and new not in out.columns}
    if ren:
        out = out.rename(columns=ren)
    # dopisz brakujące nowe
    add_cols = [c for c in NEW_SCHEMA_COLS if c not in out.columns]
    for c in add_cols:
        out[c] = np.nan
    # kolumna data
    if "data" in out.columns:
        out["data"] = pd.to_datetime(out["data"], errors="coerce")
        out = out.sort_values("data")
    return out.reset_index(drop=True)


def migrate_to_new_schema() -> None:
    """
    Jednorazowa, bezpieczna migracja całej sesji do nowych nazw.
    Migruje:
      - exec[rok][miesiac] – DataFrame'y z danymi,
      - audit[rok][miesiac] – pole 'kolumna' (stare nazwy na nowe).
    """
    _ensure_state()
    if st.session_state.get("_migration_new_schema_v1_done"):
        return

    # Exec
    ex = st.session_state["exec"]
    for y, months in list(ex.items()):
        for m, df in list(months.items()):
            if isinstance(df, pd.DataFrame):
                ex[y][m] = apply_new_schema(df)

    # Audit – przemapuj nazwy kolumn w historii
    ad = st.session_state["audit"]
    for y, months in list(ad.items()):
        for m, df in list(months.items()):
            if isinstance(df, pd.DataFrame) and "kolumna" in df.columns:
                df = df.copy()
                df["kolumna"] = df["kolumna"].map(lambda k: OLD2NEW.get(str(k), str(k)))
                ad[y][m] = _normalize_audit(df)

    st.session_state["_migration_new_schema_v1_done"] = True
    st.toast("Migracja nazw do nowego schematu zakończona.", icon="✅")


def get_month_df(year: int, month: int) -> pd.DataFrame:
    _ensure_state()
    df = st.session_state["exec"][year][month]
    return apply_new_schema(df)  # zawsze oddaj w nowym schemacie


def _normalize_df_for_save(df: pd.DataFrame) -> pd.DataFrame:
    out = apply_new_schema(df)  # wymuś schemat przed zapisem
    if "data" in out.columns:
        out["data"] = pd.to_datetime(out["data"], errors="coerce")
        out = out.sort_values("data")
    return out.reset_index(drop=True)


def save_month_df(year: int, month: int, new_df: pd.DataFrame, user: str = "GM") -> pd.DataFrame:
    """
    Zapisz miesiąc w nowym schemacie; zwróć DataFrame zmian (dla audytu).
    """
    _ensure_state()
    new_df = _normalize_df_for_save(new_df)

    old = apply_new_schema(st.session_state["exec"][year][month])
    old_i = old.set_index("data")
    new_i = new_df.set_index("data")

    # wyrównanie kolumn (pełny zbiór)
    all_cols = sorted(set(old_i.columns) | set(new_i.columns))
    old_i = old_i.reindex(columns=all_cols)
    new_i = new_i.reindex(columns=all_cols)

    neq = (old_i.fillna(np.nan).astype(object) != new_i.fillna(np.nan).astype(object))
    changes = []
    ts = datetime.now()
    for d, row in neq.iterrows():
        for c in row.index[row.values]:
            changes.append(
                {
                    "czas": ts,
                    "uzytkownik": user,
                    "data": pd.to_datetime(d),
                    "kolumna": c,  # już nowe nazwy
                    "stara": "" if pd.isna(old_i.at[d, c]) else str(old_i.at[d, c]),
                    "nowa": "" if pd.isna(new_i.at[d, c]) else str(new_i.at[d, c]),
                }
            )

    st.session_state["exec"][year][month] = new_df.reset_index(drop=True)

    if not changes:
        return pd.DataFrame(columns=["czas", "uzytkownik", "data", "kolumna", "stara", "nowa"])
    delta = pd.DataFrame(changes)
    # audit – trzymajmy wszystko w nowych nazwach
    st.session_state["audit"][year][month] = pd.concat(
        [st.session_state["audit"][year][month], _normalize_audit(delta)], ignore_index=True
    )
    return delta


def get_audit(year: int, month: int) -> pd.DataFrame:
    _ensure_state()
    return _normalize_audit(st.session_state["audit"][year][month].copy())


def split_editable(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Dzieli na dni ≤ dziś (edycja) i > dziś (podgląd)."""
    today = pd.to_datetime(date.today())
    if "data" not in df.columns:
        return df.copy(), pd.DataFrame(columns=df.columns)
    mask = df["data"] <= today
    return df.loc[mask].reset_index(drop=True), df.loc[~mask].reset_index(drop=True)

# ──────────────────────────────────────────────────────────────────────────────
# 3) KPI – wyłącznie na nowych nazwach
# ──────────────────────────────────────────────────────────────────────────────

def _num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce").fillna(0.0)


def kpi_rooms_month(df: pd.DataFrame) -> Dict[str, float]:
    df = apply_new_schema(df)
    available = float((_num(df.get("pokoje_dostepne_qty", 0)) - _num(df.get("pokoje_oos_qty", 0))).sum())
    sold = float((_num(df.get("pokoje_sprzedane_bez_qty", 0)) + _num(df.get("pokoje_sprzedane_ze_qty", 0))).sum())
    revenue = float(_num(df.get("pokoje_przychod_netto_pln", 0)).sum())

    frekw = (sold / available) if available > 0 else 0.0
    revpor = (revenue / sold) if sold > 0 else 0.0

    # koszty Pokoje = suma wszystkich kolumn z prefiksem koszt_r_
    koszt_cols = [c for c in df.columns if c.startswith("koszt_r_")]
    koszty = float(_num(df[koszt_cols].stack()).sum()) if koszt_cols else 0.0

    return {
        "zdolnosc": available,
        "sprzedane": sold,
        "frekwencja": frekw,
        "revpor": revpor,
        "k_wydzialowe": koszty,
        "wynik": revenue - koszty,
    }


def kpi_fnb_month(df: pd.DataFrame) -> Dict[str, float]:
    df = apply_new_schema(df)
    # sprzedaż F&B – wszystkie fnb_* + sprzedaz_wynajem_sali_pln
    fnb_cols = [c for c in df.columns if c.startswith("fnb_")] + ["sprzedaz_wynajem_sali_pln"]
    fnb_cols = [c for c in fnb_cols if c in df.columns]
    sprzedaz = float(_num(df[fnb_cols].stack()).sum()) if fnb_cols else 0.0

    koszt_cols = [c for c in df.columns if c.startswith("koszt_g_")]
    koszty = float(_num(df[koszt_cols].stack()).sum()) if koszt_cols else 0.0

    return {"sprzedaz_fnb": sprzedaz, "g_k_razem": koszty, "g_wynik": sprzedaz - koszty}


def kpi_rooms_ytd(exec_state: Dict, year: int, month: int) -> Dict[str, float]:
    _ensure_state()
    data = st.session_state["exec"] if not exec_state else exec_state

    avail = sold = revenue = koszty = 0.0
    for m in range(1, month + 1):
        df = apply_new_schema(data.get(year, {}).get(m, pd.DataFrame()))
        if df.empty:
            continue
        avail += float((_num(df.get("pokoje_dostepne_qty", 0)) - _num(df.get("pokoje_oos_qty", 0))).sum())
        sold += float((_num(df.get("pokoje_sprzedane_bez_qty", 0)) + _num(df.get("pokoje_sprzedane_ze_qty", 0))).sum())
        revenue += float(_num(df.get("pokoje_przychod_netto_pln", 0)).sum())
        koszt_cols = [c for c in df.columns if c.startswith("koszt_r_")]
        koszty += float(_num(df[koszt_cols].stack()).sum()) if koszt_cols else 0.0

    return {
        "zdolnosc": avail,
        "sprzedane": sold,
        "frekwencja": (sold / avail) if avail > 0 else 0.0,
        "revpor": (revenue / sold) if sold > 0 else 0.0,
        "k_wydzialowe": koszty,
        "wynik": revenue - koszty,
    }


def kpi_fnb_ytd(exec_state: Dict, year: int, month: int) -> Dict[str, float]:
    _ensure_state()
    data = st.session_state["exec"] if not exec_state else exec_state

    sprzedaz = koszty = 0.0
    for m in range(1, month + 1):
        df = apply_new_schema(data.get(year, {}).get(m, pd.DataFrame()))
        if df.empty:
            continue
        fnb_cols = [c for c in df.columns if c.startswith("fnb_")] + ["sprzedaz_wynajem_sali_pln"]
        fnb_cols = [c for c in fnb_cols if c in df.columns]
        if fnb_cols:
            sprzedaz += float(_num(df[fnb_cols].stack()).sum())
        koszt_cols = [c for c in df.columns if c.startswith("koszt_g_")]
        if koszt_cols:
            koszty += float(_num(df[koszt_cols].stack()).sum())

    return {"sprzedaz_fnb": sprzedaz, "g_k_razem": koszty, "g_wynik": sprzedaz - koszty}
