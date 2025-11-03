# =========================================
# file: wykonanie.py
# =========================================
from __future__ import annotations

from typing import Dict

import numpy as np
import pandas as pd
import streamlit as st

from state import (
    init_exec_year,
    get_month_df,
    save_month_df,
    get_audit,
    split_editable,
    missing_days,
    # listy kolumn do kalkulacji KPI:
    ROOMS_DAY_COLS,
    ROOMS_COST_PERSONNEL,
    ROOMS_COST_MATERIALS,
    ROOMS_COST_SERVICES,
    ROOMS_COST_OTHER,
    FNB_REVENUE_DAY_COLS,
    FNB_COST_RAW,
    FNB_COST_PERSONNEL,
    FNB_COST_MATERIALS,
    FNB_COST_SERVICES,
)

MONTHS_PL = ["sty", "lut", "mar", "kwi", "maj", "cze", "lip", "sie", "wrz", "paź", "lis", "gru"]

st.set_page_config(page_title="Wykonanie – dziennik", layout="wide")


# ---------- KPI helpers ----------
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

    k_os = _sum(df, ROOMS_COST_PERSONNEL)
    k_mat = _sum(df, ROOMS_COST_MATERIALS)
    k_usl = _sum(df, ROOMS_COST_SERVICES)
    k_poz = _sum(df, ROOMS_COST_OTHER)
    k_all = k_os + k_mat + k_usl + k_poz

    revpor = (rev_rooms / sold) if sold > 0 else 0.0
    wynik = rev_rooms - k_all
    cost_per_sold = (k_all / sold) if sold > 0 else 0.0

    return {
        "zdolnosc": rooms_available,
        "sprzedane": sold,
        "frekwencja": float(occ),
        "revpor": float(revpor),
        "sprzedaz_pokoi": rev_rooms,
        "k_wydzialowe": float(k_all),
        "wynik": float(wynik),
        "koszt_na_sprzedany_pokoj": float(cost_per_sold),
    }


def kpi_rooms_ytd(exec_state: Dict[int, Dict[int, pd.DataFrame]], year: int, month: int) -> Dict[str, float]:
    frames = [exec_state[year][m] for m in range(1, month + 1)]
    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["pokoje_do_sprzedania"])
    return kpi_rooms_month(df)


def kpi_fnb_month(df: pd.DataFrame) -> Dict[str, float]:
    rev = _sum(df, FNB_REVENUE_DAY_COLS)
    k_raw = _sum(df, FNB_COST_RAW)
    k_os = _sum(df, FNB_COST_PERSONNEL)
    k_mat = _sum(df, FNB_COST_MATERIALS)
    k_usl = _sum(df, FNB_COST_SERVICES)
    k_all = k_raw + k_os + k_mat + k_usl
    wynik = rev - k_all
    return {
        "sprzedaz_fnb": float(rev),
        "g_koszt_surowca": float(k_raw),
        "g_k_razem": float(k_all),
        "g_wynik": float(wynik),
    }


def kpi_fnb_ytd(exec_state: Dict[int, Dict[int, pd.DataFrame]], year: int, month: int) -> Dict[str, float]:
    frames = [exec_state[year][m] for m in range(1, month + 1)]
    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["fnb_sniadania_pakietowe"])
    return kpi_fnb_month(df)


# ---------- Page ----------
def render(readonly: bool = False) -> None:
    st.header("Wykonanie – dziennik i podsumowania")

    # Plik Google Drive (ID lub URL) – domyślnie z secrets; UI może nadpisać na sesję
    default_file = st.secrets.get("PLAN_FILE_ID") or st.secrets.get("PLAN_FILE_URL") or ""
    drive_file = st.sidebar.text_input(
        "Plik Google Drive (ID lub URL)",
        value=st.session_state.get("drive_plan_file", default_file),
        help="ID lub pełny URL tego samego Excela (Plan Finansowy Hotele).",
    )
    if st.sidebar.button("Użyj tego pliku", type="primary"):
        st.session_state["drive_plan_file"] = drive_file
        st.success("Ustawiono plik Google Drive do zapisu/odczytu arkuszy WYKONANIE_YYYY_MM.")

    year = int(st.sidebar.number_input("Rok", min_value=2000, max_value=2100, value=2025, step=1))
    init_exec_year(year, drive_id_or_url=st.session_state.get("drive_plan_file", ""))

    month = int(
        st.sidebar.selectbox(
            "Miesiąc", options=list(range(1, 13)), format_func=lambda m: f"{MONTHS_PL[m-1]} ({m:02d})"
        )
    )
    st.sidebar.caption("Po zapisie zmienione komórki podświetlą się **na żółto**.\nDni > dziś są tylko do podglądu.")

    _month_editor(year, month, readonly)

    st.markdown("---")
    _kpis(year, month)


def _month_editor(year: int, month: int, readonly: bool) -> None:
    st.subheader(f"Edycja danych – {MONTHS_PL[month-1].capitalize()} {year}")

    df_full = get_month_df(year, month)
    df_edit, df_future = split_editable(df_full)

    # --- Dni do dziś (edytowalne) ---
    st.markdown("#### Dni do dziś (edytowalne)")
    cfg = {"data": st.column_config.DateColumn("Data")}
    for c in df_edit.columns:
        if c == "data":
            continue
        cfg[c] = st.column_config.NumberColumn(c, step=1.0, format="%.2f")

    if readonly:
        st.dataframe(df_edit, use_container_width=True, hide_index=True)
        if not df_future.empty:
            st.markdown("#### Dni przyszłe (podgląd)")
            st.dataframe(df_future, use_container_width=True, hide_index=True)
        return

    edited = st.data_editor(
        df_edit,
        column_config=cfg,
        num_rows="fixed",
        use_container_width=True,
        hide_index=True,
        key=f"editor_{year}_{month}",
    )

    # --- Dni przyszłe (podgląd) ---
    if not df_future.empty:
        st.markdown("#### Dni przyszłe (podgląd)")
        st.dataframe(df_future, use_container_width=True, hide_index=True)

    left, right = st.columns([1, 3])

    with left:
        who = st.text_input("Kto zapisuje?", value="GM", help="Imię / skrót użytkownika do logu.")
        if st.button("Zapisz zmiany", type="primary", key=f"save_{year}_{month}"):
            new_full = pd.concat([edited, df_future], ignore_index=True)
            changes = save_month_df(year, month, new_full, user=who)
            if changes.empty:
                st.info("Brak zmian.")
            else:
                st.success(f"Zapisano {len(changes)} zmian (wysłano do tego samego pliku na Drive).")
                st.session_state[f"last_changes_{year}_{month}"] = changes

    with right:
        # podpowiedź nieuzupełnionych dni (na bazie przychodów pokoi)
        missing = list(
            missing_days(pd.concat([edited, df_future], ignore_index=True)).dt.strftime("%Y-%m-%d")
        )
        if missing:
            st.warning(f"Brakuje danych (sprzedaż pokoi) dla dni: {', '.join(missing)}")

        # zmiany ostatniego zapisu + podświetlenie różnic
        changes = st.session_state.get(f"last_changes_{year}_{month}")
        if changes is not None and not changes.empty:
            st.subheader("Zmiany (ostatni zapis)")
            st.dataframe(changes, use_container_width=True, hide_index=True)

            st.subheader("Podgląd po zapisie (zmienione na żółto)")
            before = df_full.set_index("data").sort_index()
            after = pd.concat([edited, df_future], ignore_index=True).set_index("data").sort_index()
            before, after = before.align(after, join="outer", axis=0)
            cols = [c for c in after.columns if c in before.columns and c != "data"]
            mask = after[cols] != before[cols]
            styled = after.style.apply(
                lambda df_: (mask).replace({True: "background-color: #fff3cd", False: ""}),
                axis=None,
                subset=cols,
            )
            st.dataframe(styled, use_container_width=True, hide_index=True)

    # --- Audit log ---
    st.subheader("Historia zmian (audit log)")
    audit = get_audit(year, month)
    if audit.empty:
        st.write("Brak zmian w tym miesiącu.")
    else:
        st.dataframe(audit.sort_values("czas", ascending=False), use_container_width=True, hide_index=True)


def _kpis(year: int, month: int) -> None:
    st.subheader("Podsumowania KPI")
    df = get_month_df(year, month)

    # Miesiąc
    r_m = kpi_rooms_month(df)
    f_m = kpi_fnb_month(df)

    # Narastająco (YTD)
    exec_state = st.session_state.get("exec", {})
    r_y = kpi_rooms_ytd(exec_state, year, month)
    f_y = kpi_fnb_ytd(exec_state, year, month)

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Zdolność eksploatacyjna", f"{r_m['zdolnosc']:.0f}", delta=f"YTD {r_y['zdolnosc']:.0f}")
    k2.metric("Sprzedane pokojonoce", f"{r_m['sprzedane']:.0f}", delta=f"YTD {r_y['sprzedane']:.0f}")
    k3.metric("Frekwencja", f"{r_m['frekwencja']*100:.1f}%", delta=f"YTD {r_y['frekwencja']*100:.1f}%")
    k4.metric("RevPOR", f"{r_m['revpor']:.2f} zł", delta=f"YTD {r_y['revpor']:.2f} zł")
    k5.metric("Koszty wydziałowe (Pokoje)", f"{r_m['k_wydzialowe']:.2f} zł", delta=f"YTD {r_y['k_wydzialowe']:.2f} zł")
    k6.metric("Wynik (Pokoje)", f"{r_m['wynik']:.2f} zł", delta=f"YTD {r_y['wynik']:.2f} zł")

    g1, g2, g3 = st.columns(3)
    g1.metric("Sprzedaż gastronomii", f"{f_m['sprzedaz_fnb']:.2f} zł", delta=f"YTD {f_y['sprzedaz_fnb']:.2f} zł")
    g2.metric("Koszty F&B", f"{f_m['g_k_razem']:.2f} zł", delta=f"YTD {f_y['g_k_razem']:.2f} zł")
    g3.metric("Wynik F&B", f"{f_m['g_wynik']:.2f} zł", delta=f"YTD {f_y['g_wynik']:.2f} zł")


# Uruchamianie lokalne (opcjonalnie)
if __name__ == "__main__":
    render(readonly=False)
