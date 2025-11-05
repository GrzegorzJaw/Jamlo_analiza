# pages/wykonanie.py
from __future__ import annotations

import io
import os
from datetime import date
from typing import Iterable, List, Optional, Dict

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
REQUIRED_COLS_DEFAULT = [
    "pokoje_do_sprzedania","sprzedane_pokoje_bez",
    "sprzedane_pokoje_ze","przychody_pokoje_netto",
]


def render(readonly: bool = False) -> None:
    # — Context —
    role  = st.session_state.get("role", "GM")
    year  = int(st.session_state.get("year", 2025))
    month = int(st.session_state.get("month", 1))
    is_inv = readonly or (role == "INV")
    init_exec_year(year)

    # — Header + month nav —
    c1, c2, c3 = st.columns([7, 1, 1])
    with c1:
        st.header("Wykonanie – dziennik i podsumowania")
    with c2:
        if st.button("◀︎", key=f"wyk_prev_{year}_{month}"):
            m, y = (12, year - 1) if month == 1 else (month - 1, year)
            st.session_state["month"], st.session_state["year"] = m, y
            st.rerun()
    with c3:
        if st.button("▶︎", key=f"wyk_next_{year}_{month}"):
            m, y = (1, year + 1) if month == 12 else (month + 1, year)
            st.session_state["month"], st.session_state["year"] = m, y
            st.rerun()

    st.subheader(f"Edycja danych – {MONTHS_PL[month-1].capitalize()} {year}")

    # — Data —
    df_full = get_month_df(year, month)
    df_edit, df_future = split_editable(df_full)

    # — Dynamic group map —
    groups = _detect_groups(df_edit)
    groups["Wszystkie"] = [c for c in df_edit.columns if c != "data"]

    # — Quick filters —
    fc1, fc2 = st.columns([2, 3])
    with fc1:
        only_missing = st.checkbox(
            "Pokaż tylko wiersze nieuzupełnione",
            value=False,
            key=f"only_missing_{year}_{month}",
        )
    with fc2:
        group = st.selectbox(
            "Grupa kolumn",
            list(groups.keys()),
            index=(list(groups.keys()).index("Pokoje") if "Pokoje" in groups else 0),
            key=f"group_{year}_{month}",
        )

    group_cols = [c for c in groups.get(group, []) if c in df_edit.columns]
    subset_cols_for_style = group_cols or [c for c in REQUIRED_COLS_DEFAULT if c in df_edit.columns]

    if only_missing:
        base_cols = group_cols or subset_cols_for_style
        view_df = _filter_missing_rows(df_edit, base_cols)
    else:
        view_df = df_edit

    # — Editable days (to today) —
    st.markdown("#### Dni do dziś")
    if is_inv:
        st.info("Tryb podglądu – edycja wyłączona (INV).")
        st.dataframe(_style_missing(view_df, subset_cols=subset_cols_for_style), width="stretch", hide_index=True)
        all_now = pd.concat([df_edit, df_future], ignore_index=True)
    else:
        cfg: Dict[str, st.column_config.BaseColumn] = {
            "data": st.column_config.DateColumn("Data", disabled=True)
        }
        for c in view_df.columns:
            if c != "data":
                cfg[c] = st.column_config.NumberColumn(c, step=1.0, format="%.2f")

        # 👇 klucz zależny od filtrów → brak kolizji cache
        editor_key = f"editor_{year}_{month}_{_group_key(group)}_{int(only_missing)}"
        edited_view = st.data_editor(
            view_df,
            column_config=cfg,
            num_rows="fixed",
            width="stretch",
            hide_index=True,
            key=editor_key,
        )

        left, right = st.columns([1, 3])
        with left:
            who = st.text_input("Kto zapisuje?", value="GM")
            if st.button("Zapisz w sesji", type="primary", key=f"save_{year}_{month}"):
                merged_edit = _merge_back(df_edit, edited_view)
                new_full = pd.concat([merged_edit, df_future], ignore_index=True)
                changes = save_month_df(year, month, new_full, user=who)
                st.success(f"Zapisano {len(changes)} zmian.") if not changes.empty else st.info("Brak zmian.")
                st.session_state[f"last_changes_{year}_{month}"] = changes

        with right:
            st.markdown("**Podgląd braków (na czerwono)**")
            st.dataframe(
                _style_missing(edited_view, subset_cols=subset_cols_for_style),
                width="stretch", hide_index=True,
            )

            changes = st.session_state.get(f"last_changes_{year}_{month}")
            if changes is not None and not changes.empty:
                st.subheader("Zmiany (ostatni zapis)")
                st.dataframe(changes, width="stretch", hide_index=True)

                st.subheader("Podgląd po zapisie (zmienione na żółto)")
                before = df_full.set_index("data").sort_index()
                after_all = _merge_back(df_edit, edited_view).set_index("data").sort_index()
                before, after_all = before.align(after_all, join="outer", axis=0)
                cols = [c for c in after_all.columns if c in before.columns and c != "data"]
                mask = after_all[cols] != before[cols]
                styled = after_all.style.apply(
                    lambda _: mask.replace({True: "background-color: #fff3cd", False: ""}),
                    axis=None,
                    subset=cols,
                )
                st.dataframe(styled, width="stretch", hide_index=True)

        all_now = pd.concat([_merge_back(df_edit, edited_view), df_future], ignore_index=True)

    # — Future days —
    if not df_future.empty:
        st.markdown("#### Dni przyszłe (podgląd)")
        st.dataframe(df_future, width="stretch", hide_index=True)

    # — Audit —
    st.subheader("Historia zmian (audit log)")
    audit = get_audit(year, month)
    st.write("Brak zmian w tym miesiącu.") if audit.empty else st.dataframe(
        audit.sort_values("czas", ascending=False), width="stretch", hide_index=True
    )

    # — KPI —
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

    # — Export —
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


# ===================== helpers =====================

def _group_key(group: str) -> str:
    return group.lower().replace(" ", "_").replace("ł", "l").replace("ś", "s").replace("ż", "z").replace("ź", "z").replace("ą","a").replace("ę","e").replace("ó","o").replace("ń","n").replace("ć","c")


def _detect_groups(df: pd.DataFrame) -> Dict[str, List[str]]:
    cols = set(df.columns) - {"data"}
    pokoje = [c for c in cols if c.startswith(("pokoje_", "sprzedane_pokoje_", "przychody_pokoje_"))]
    dzial = [c for c in cols if c == "fnb_wynajem_sali"]
    gastro = [c for c in cols if c.startswith("fnb_") and c not in dzial]
    inne = [c for c in cols if (c.startswith("przychody_") and not c.startswith("przychody_pokoje_")) or c.startswith("proc_pokoi_")]
    koszty = [c for c in cols if c.startswith(("r_", "g_"))]
    return {
        "Pokoje": sorted(pokoje),
        "Gastronomia": sorted(gastro),
        "Dział Sprzedaży": sorted(dzial),
        "Inne Centra": sorted(inne),
        "Koszty": sorted(koszty),
    }


def _filter_missing_rows(df: pd.DataFrame, cols: Iterable[str]) -> pd.DataFrame:
    cols = [c for c in cols if c in df.columns]
    if not cols:
        return df
    # NaN lub 0 po konwersji numerycznej
    miss = df[cols].isna()
    num = df[cols].apply(pd.to_numeric, errors="coerce")
    miss |= num.eq(0.0)
    mask = miss.any(axis=1)
    return df.loc[mask].reset_index(drop=True)


def _merge_back(original: pd.DataFrame, edited_view: pd.DataFrame) -> pd.DataFrame:
    if edited_view.empty:
        return original.copy()
    base = original.set_index("data")
    patch = edited_view.set_index("data")
    common_cols = [c for c in patch.columns if c in base.columns]
    base.loc[patch.index, common_cols] = patch[common_cols]
    return base.reset_index()


def _style_missing(df_like: pd.DataFrame, *, subset_cols: Optional[Iterable[str]] = None) -> pd.io.formats.style.Styler:
    df = df_like.copy()
    today = pd.to_datetime(date.today())
    if "data" in df.columns:
        df = df[df["data"] <= today]
    cols = [c for c in (subset_cols or REQUIRED_COLS_DEFAULT) if c in df.columns]
    if not cols:
        return df.style

    def style_subset(subdf: pd.DataFrame) -> pd.DataFrame:
        miss = subdf.isna()
        num = subdf.apply(pd.to_numeric, errors="coerce")
        miss |= num.eq(0.0)
        return miss.replace({True: "background-color: #ffdddd", False: ""})

    return df.style.apply(style_subset, axis=None, subset=cols)


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
