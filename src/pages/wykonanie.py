# pages/wykonanie.py
from __future__ import annotations

import io
import os
from datetime import date
import pandas as pd
import streamlit as st

from core.state_local import (
    init_exec_year,
    get_month_df,
    save_month_df,
    get_audit,
    split_editable,
    kpi_rooms_month,
    kpi_rooms_ytd,
    kpi_fnb_month,
    kpi_fnb_ytd,
)

MONTHS_PL = ["sty","lut","mar","kwi","maj","cze","lip","sie","wrz","paź","lis","gru"]
# Kluczowe pola, które traktujemy jako „wymagane” dla dnia
REQUIRED_COLS = [
    "pokoje_do_sprzedania",
    "sprzedane_pokoje_bez",
    "sprzedane_pokoje_ze",
    "przychody_pokoje_netto",
]


def render(readonly: bool = False) -> None:
    role  = st.session_state.get("role", "GM")
    year  = int(st.session_state.get("year", 2025))
    month = int(st.session_state.get("month", 1))
    is_inv = readonly or (role == "INV")

    init_exec_year(year)

    # Tytuł + strzałki miesiąca
    c1, c2, c3 = st.columns([7, 1, 1])
    with c1:
        st.header("Wykonanie – dziennik i podsumowania")
    with c2:
        if st.button("◀︎", key=f"wyk_prev_{year}_{month}", help="Poprzedni miesiąc"):
            m, y = month - 1, year
            if m < 1:
                m, y = 12, year - 1
            st.session_state["month"], st.session_state["year"] = m, y
            st.rerun()
    with c3:
        if st.button("▶︎", key=f"wyk_next_{year}_{month}", help="Następny miesiąc"):
            m, y = month + 1, year
            if m > 12:
                m, y = 1, year + 1
            st.session_state["month"], st.session_state["year"] = m, y
            st.rerun()

    st.subheader(f"Edycja danych – {MONTHS_PL[month-1].capitalize()} {year}")

    df_full = get_month_df(year, month)
    df_edit, df_future = split_editable(df_full)

    # ===== Dni do dziś =====
    st.markdown("#### Dni do dziś")
    if is_inv:
        # INV – widok tylko do odczytu, od razu z podświetleniem braków
        st.info("Tryb podglądu – edycja wyłączona (INV).")
        st.dataframe(_style_missing(df_edit), width="stretch", hide_index=True)
        all_now = pd.concat([df_edit, df_future], ignore_index=True)
    else:
        # GM – edytor
        cfg = {"data": st.column_config.DateColumn("Data")}
        for c in df_edit.columns:
            if c != "data":
                cfg[c] = st.column_config.NumberColumn(c, step=1.0, format="%.2f")

        edited = st.data_editor(
            df_edit,
            column_config=cfg,
            num_rows="fixed",
            width="stretch",
            hide_index=True,
            key=f"editor_{year}_{month}",
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
            # Zamiast komunikatu o brakach – podświetlenie braków
            st.markdown("**Podgląd braków (na czerwono)**")
            st.dataframe(_style_missing(edited), width="stretch", hide_index=True)

            changes = st.session_state.get(f"last_changes_{year}_{month}")
            if changes is not None and not changes.empty:
                st.subheader("Zmiany (ostatni zapis)")
                st.dataframe(changes, width="stretch", hide_index=True)

                st.subheader("Podgląd po zapisie (zmienione na żółto)")
                before = df_full.set_index("data").sort_index()
                after = pd.concat([edited, df_future], ignore_index=True).set_index("data").sort_index()
                before, after = before.align(after, join="outer", axis=0)
                cols = [c for c in after.columns if c in before.columns and c != "data"]
                mask = after[cols] != before[cols]
                styled = after.style.apply(
                    lambda _: mask.replace({True: "background-color: #fff3cd", False: ""}),
                    axis=None,
                    subset=cols,
                )
                st.dataframe(styled, width="stretch", hide_index=True)

        all_now = pd.concat([edited, df_future], ignore_index=True)

    # ===== Dni przyszłe =====
    if not df_future.empty:
        st.markdown("#### Dni przyszłe (podgląd)")
        st.dataframe(df_future, width="stretch", hide_index=True)

    # ===== Audit log =====
    st.subheader("Historia zmian (audit log)")
    audit = get_audit(year, month)
    if audit.empty:
        st.write("Brak zmian w tym miesiącu.")
    else:
        st.dataframe(audit.sort_values("czas", ascending=False), width="stretch", hide_index=True)

    # ===== KPI =====
    st.subheader("Podsumowania KPI")
    r_m = kpi_rooms_month(all_now)
    f_m = kpi_fnb_month(all_now)
    exec_state = st.session_state.get("exec", {})
    r_y = kpi_rooms_ytd(exec_state, year, month)
    f_y = kpi_fnb_ytd(exec_state, year, month)

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Zdolność eksploatacyjna", f"{r_m['zdolnosc']:.0f}", delta=f"YTD {r_y['zdolnosc']:.0f}")
    k2.metric("Sprzedane pokojonoce", f"{r_m['sprzedane']:.0f}", delta=f"YTD {r_y['sprzedane']:.0f}")
    k3.metric("Frekwencja", f"{r_m['frekwencja']*100:.1f}%", delta=f"YTD {r_y['frekwencja']*100:.1f}%")
    k4.metric("RevPOR", f"{r_m['revpor']:.2f} zł", delta=f"YTD {r_y['revpor']:.2f} zł")
    k5.metric("Koszty wydziałowe", f"{r_m['k_wydzialowe']:.2f} zł", delta=f"YTD {r_y['k_wydzialowe']:.2f} zł")
    k6.metric("Wynik (Pokoje)", f"{r_m['wynik']:.2f} zł", delta=f"YTD {r_y['wynik']:.2f} zł")

    g1, g2, g3 = st.columns(3)
    g1.metric("Sprzedaż gastronomii", f"{f_m['sprzedaz_fnb']:.2f} zł", delta=f"YTD {f_y['sprzedaz_fnb']:.2f} zł")
    g2.metric("Koszty F&B", f"{f_m['g_k_razem']:.2f} zł", delta=f"YTD {f_y['g_k_razem']:.2f} zł")
    g3.metric("Wynik F&B", f"{f_m['g_wynik']:.2f} zł", delta=f"YTD {f_y['g_wynik']:.2f} zł")

    # ===== Eksport =====
    st.subheader("Eksport do Excela")
    if st.button("Eksportuj wszystkie lata/miesiące do XLSX", type="secondary", key="export_all_xlsx"):
        try:
            buffer = _export_all_to_excel_bytes()
            st.success("Wyeksportowano. Poniżej przycisk pobierania.")
            st.download_button(
                "Pobierz XLSX",
                data=buffer.getvalue(),
                file_name="wykonanie_export.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="export_download_btn",
            )
            try:
                os.makedirs("/mnt/data", exist_ok=True)
                with open("/mnt/data/wykonanie_export.xlsx", "wb") as f:
                    f.write(buffer.getvalue())
                st.caption("Zapisano również: /mnt/data/wykonanie_export.xlsx")
            except Exception:
                pass
        except Exception as e:
            st.error(f"Nie udało się wyeksportować: {e}")


def _style_missing(df_edit: pd.DataFrame) -> pd.io.formats.style.Styler:
    """Zwraca Styler z czerwonym podświetleniem braków w wymaganych kolumnach."""
    df = df_edit.copy()
    # Tylko dni do dziś – df_edit już je reprezentuje, ale utnij na wszelki
    today = pd.to_datetime(date.today())
    if "data" in df.columns:
        df = df[df["data"] <= today]

    cols = [c for c in REQUIRED_COLS if c in df.columns]
    if not cols:
        return df.style  # nic do stylowania

    def _mask(_df: pd.DataFrame) -> pd.DataFrame:
        m = pd.DataFrame(False, index=_df.index, columns=_df.columns)
        for c in cols:
            # brak = NaN lub == 0
            m[c] = _df[c].isna() | (_df[c].astype(float) == 0.0)
        return m

    mask = _mask(df)
    return df.style.apply(lambda _: mask.replace({True: "background-color: #ffdddd", False: ""}), axis=None, subset=cols)


def _export_all_to_excel_bytes() -> io.BytesIO:
    exec_state = st.session_state.get("exec", {})
    if not exec_state:
        raise RuntimeError("Brak danych w sesji do eksportu.")
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as wr:
        for y, months in exec_state.items():
            for m, df in months.items():
                sheet = f"WYKONANIE_{int(y)}_{int(m):02d}"[:31]
                df.to_excel(wr, index=False, sheet_name=sheet)
    buf.seek(0)
    return buf
