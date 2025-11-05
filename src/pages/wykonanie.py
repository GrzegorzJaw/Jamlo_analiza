# =========================================
# file: pages/wykonanie.py
# Lokalna praca na danych (session_state), bez wczytywania z chmury
# =========================================
from __future__ import annotations

from typing import Dict

import pandas as pd
import streamlit as st

from core.state_local import (
    # stan + CRUD
    init_exec_year,
    get_month_df,
    save_month_df,
    get_audit,
    split_editable,
    missing_days,
    export_all_to_excel,
    # kolumny + KPI
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
    kpi_rooms_month,
    kpi_rooms_ytd,
    kpi_fnb_month,
    kpi_fnb_ytd,
)

MONTHS_PL = ["sty", "lut", "mar", "kwi", "maj", "cze", "lip", "sie", "wrz", "paź", "lis", "gru"]


def render(readonly: bool = False) -> None:
    """Widok Wykonania – korzysta z kontekstu ustawionego w app.py."""
    role = st.session_state.get("role", "GM")
    year = int(st.session_state.get("year", 2025))
    month = int(st.session_state.get("month", 1))
    is_inv = readonly or (role == "INV")  # INV wymusza podgląd

    init_exec_year(year)  # tworzy puste DF-y, jeśli nie istnieją

    st.header("Wykonanie – dziennik i podsumowania (lokalnie, bez wczytywania)")
    st.caption("Dni > dziś są tylko w podglądzie. Zmiany zapisywane są w sesji + audit log.")

    _month_editor(year, month, is_inv)
    st.markdown("---")
    _kpis(year, month)
    st.markdown("---")
    _export_area()


def _month_editor(year: int, month: int, readonly: bool) -> None:
    st.subheader(f"Edycja danych – {MONTHS_PL[month-1].capitalize()} {year}")

    df_full = get_month_df(year, month)
    df_edit, df_future = split_editable(df_full)

    st.markdown("#### Dni do dziś")
    if readonly:
        st.info("Tryb podglądu – edycja wyłączona (INV).")
        st.dataframe(df_edit, use_container_width=True, hide_index=True)
    else:
        cfg = {"data": st.column_config.DateColumn("Data")}
        for c in df_edit.columns:
            if c == "data":
                continue
            cfg[c] = st.column_config.NumberColumn(c, step=1.0, format="%.2f")

        edited = st.data_editor(
            df_edit,
            column_config=cfg,
            num_rows="fixed",
            use_container_width=True,
            hide_index=True,
            key=f"editor_{year}_{month}",  # klucz per miesiąc – brak kolizji
        )

        left, right = st.columns([1, 3])
        with left:
            who = st.text_input("Kto zapisuje?", value="GM", help="Imię / skrót do logu zmian.")
            if st.button("Zapisz w sesji", type="primary", key=f"save_{year}_{month}"):
                new_full = pd.concat([edited, df_future], ignore_index=True)
                changes = save_month_df(year, month, new_full, user=who)
                if changes.empty:
                    st.info("Brak zmian.")
                else:
                    st.success(f"Zapisano {len(changes)} zmian.")
                    st.session_state[f"last_changes_{year}_{month}"] = changes

        with right:
            all_now = pd.concat([edited, df_future], ignore_index=True)
            missing = list(all_now.loc[all_now["przychody_pokoje_netto"] <= 0.0, "data"].dt.strftime("%Y-%m-%d"))
            if missing:
                st.warning(f"Brakuje danych (sprzedaż pokoi) dla dni: {', '.join(missing)}")

            changes = st.session_state.get(f"last_changes_{year}_{month}")
            if changes is not None and not changes.empty:
                st.subheader("Zmiany (ostatni zapis)")
                st.dataframe(changes, use_container_width=True, hide_index=True)

                st.subheader("Podgląd po zapisie (zmienione na żółto)")
                before = df_full.set_index("data").sort_index()
                after = all_now.set_index("data").sort_index()
                before, after = before.align(after, join="outer", axis=0)
                cols = [c for c in after.columns if c in before.columns and c != "data"]
                mask = after[cols] != before[cols]
                styled = after.style.apply(
                    lambda _: mask.replace({True: "background-color: #fff3cd", False: ""}),
                    axis=None,
                    subset=cols,
                )
                st.dataframe(styled, use_container_width=True, hide_index=True)

    if not df_future.empty:
        st.markdown("#### Dni przyszłe (podgląd)")
        st.dataframe(df_future, use_container_width=True, hide_index=True)

    st.subheader("Historia zmian (audit log)")
    audit = get_audit(year, month)
    if audit.empty:
        st.write("Brak zmian w tym miesiącu.")
    else:
        st.dataframe(audit.sort_values("czas", ascending=False), use_container_width=True, hide_index=True)


def _kpis(year: int, month: int) -> None:
    st.subheader("Podsumowania KPI")

    df = get_month_df(year, month)
    r_m = kpi_rooms_month(df)
    f_m = kpi_fnb_month(df)

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


def _export_area() -> None:
    st.subheader("Eksport do Excela (na końcu pracy)")
    export_path = "/mnt/data/wykonanie_export.xlsx"
    if st.button("Eksportuj wszystkie lata/miesiące do XLSX", type="secondary"):
        try:
            path = export_all_to_excel(export_path)
            st.success("Wyeksportowano. Poniżej przycisk pobierania.")
            with open(path, "rb") as f:
                st.download_button(
                    "Pobierz XLSX",
                    data=f.read(),
                    file_name="wykonanie_export.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
        except Exception as e:
            st.error(f"Nie udało się wyeksportować: {e}")
