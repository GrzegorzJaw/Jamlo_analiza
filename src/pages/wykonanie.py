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

# ───── Nowe nazwy kolumn (spójne prefiksy) ─────
COLMAP_OLD2NEW: Dict[str, str] = {
    # POKOJE
    "pokoje_do_sprzedania": "pokoje_dostepne_qty",
    "pokoje_oos": "pokoje_oos_qty",
    "sprzedane_pokoje_bez": "pokoje_sprzedane_bez_qty",
    "sprzedane_pokoje_ze": "pokoje_sprzedane_ze_qty",
    "przychody_pokoje_netto": "pokoje_przychod_netto_pln",
    # F&B
    "fnb_sniadania_pakietowe": "fnb_sniadania_pakietowe_pln",
    "fnb_kolacje_pakietowe": "fnb_kolacje_pakietowe_pln",
    "fnb_zywnosc_a_la_carte": "fnb_zywnosc_a_la_carte_pln",
    "fnb_napoje_a_la_carte": "fnb_napoje_a_la_carte_pln",
    "fnb_zywnosc_bankiety": "fnb_zywnosc_bankiety_pln",
    "fnb_napoje_bankiety": "fnb_napoje_bankiety_pln",
    "fnb_wynajem_sali": "sprzedaz_wynajem_sali_pln",
    "fnb_catering": "fnb_catering_pln",
    # INNE CENTRA
    "proc_pokoi_parking": "inne_proc_pokoi_parking_pct",
    "przychody_parking": "inne_parking_przychod_pln",
    "przychody_sklep_recepcyjny": "inne_sklep_recepcja_przychod_pln",
    "przychody_pralnia_gosci": "inne_pralnia_gosci_przychod_pln",
    "przychody_transport_gosci": "inne_transport_przychod_pln",
    "przychody_rekreacja": "inne_rekreacja_przychod_pln",
    "przychody_pozostale": "inne_pozostale_przychod_pln",
    # KOSZTY — Pokoje
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
    # KOSZTY — F&B
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
NEW2OLD: Dict[str, str] = {new: old for old, new in COLMAP_OLD2NEW.items()}

DISPLAY_LABELS: Dict[str, str] = {
    # (etykiety – jak ustaliliśmy wcześniej; skrócone tu dla czytelności)
    "pokoje_dostepne_qty": "🛏️ Pokoje do sprzedaży",
    "pokoje_oos_qty": "🚫 Pokoje OOS",
    "pokoje_sprzedane_bez_qty": "🛏️ Sprzedane BEZ śn.",
    "pokoje_sprzedane_ze_qty": "🥐 Sprzedane ZE śn.",
    "pokoje_przychod_netto_pln": "💰 Przychody pokoje (netto)",
    "fnb_sniadania_pakietowe_pln": "🥐 Śniadania pakietowe",
    "fnb_kolacje_pakietowe_pln": "🍽️ Kolacje pakietowe",
    "fnb_zywnosc_a_la_carte_pln": "🍲 Żywność a la carte",
    "fnb_napoje_a_la_carte_pln": "🥤 Napoje a la carte",
    "fnb_zywnosc_bankiety_pln": "🎉 Żywność bankiety",
    "fnb_napoje_bankiety_pln": "🥂 Napoje bankiety",
    "fnb_catering_pln": "🧺 Catering",
    "sprzedaz_wynajem_sali_pln": "🏢 Wynajem sal",
    "inne_proc_pokoi_parking_pct": "🅿️ % pokoi z parkingiem",
    "inne_parking_przychod_pln": "🅿️ Przychody parking",
    "inne_sklep_recepcja_przychod_pln": "🛒 Sklep recepcyjny",
    "inne_pralnia_gosci_przychod_pln": "🧺 Pralnia (goście)",
    "inne_transport_przychod_pln": "🚖 Transport (goście)",
    "inne_rekreacja_przychod_pln": "🏊 Rekreacja",
    "inne_pozostale_przychod_pln": "➕ Pozostałe przychody",
    # … (reszta kosztów jak poprzednio)
}

MONTHS_PL = ["sty","lut","mar","kwi","maj","cze","lip","sie","wrz","paź","lis","gru"]
REQUIRED_COLS_DEFAULT = [
    "pokoje_dostepne_qty","pokoje_sprzedane_bez_qty",
    "pokoje_sprzedane_ze_qty","pokoje_przychod_netto_pln",
]

# ───── Migracja nazw w sesji (stare → nowe) ─────
def migrate_exec_session() -> None:
    exec_state = st.session_state.get("exec")
    if not isinstance(exec_state, dict):
        return
    marker_key = "_migrated_cols_v1"
    if st.session_state.get(marker_key):
        return
    changed = 0
    for y, months in list(exec_state.items()):
        if not isinstance(months, dict):
            continue
        for m, df in list(months.items()):
            if not isinstance(df, pd.DataFrame):
                continue
            ren_map = {old: new for old, new in COLMAP_OLD2NEW.items() if old in df.columns}
            if ren_map:
                exec_state[y][m] = df.rename(columns=ren_map)
                changed += 1
    st.session_state[marker_key] = True
    if changed:
        st.toast(f"Zastosowano migrację nazw kolumn w {changed} arkuszach.", icon="✅")

# ───── Adapter do KPI (nowe → stare) ─────
def _to_old_cols_df(df: pd.DataFrame) -> pd.DataFrame:
    # tylko jeśli starej kolumny brakuje
    ren = {new: old for new, old in NEW2OLD.items() if new in df.columns and old not in df.columns}
    return df.rename(columns=ren)

def _to_old_cols_exec(exec_state: Dict) -> Dict:
    out: Dict = {}
    if not isinstance(exec_state, dict):
        return out
    for y, months in exec_state.items():
        out[y] = {}
        if not isinstance(months, dict):
            continue
        for m, df in months.items():
            if isinstance(df, pd.DataFrame):
                out[y][m] = _to_old_cols_df(df)
    return out

# ───── helpers: grupy/filtry/styl ─────
def _to_numeric_series(s: pd.Series) -> pd.Series:
    if s.dtype == object:
        s = s.astype(str).str.strip().replace({"": None, "None": None, "nan": None})
        s = s.str.replace(" ", "", regex=False).str.replace("\xa0", "", regex=False)
        s = s.str.replace(",", ".", regex=False)
    return pd.to_numeric(s, errors="coerce")

def _is_missing_frame(df_sub: pd.DataFrame) -> pd.DataFrame:
    num = df_sub.apply(_to_numeric_series)
    miss = num.isna() | num.eq(0.0)
    if any(df_sub.dtypes == object):
        empty = df_sub.astype(str).str.strip().eq("")
        miss = miss | empty
    return miss

def _detect_groups(df: pd.DataFrame) -> Dict[str, List[str]]:
    cols = set(df.columns) - {"data"}
    return {
        "Pokoje": sorted([c for c in cols if c.startswith("pokoje_")]),
        "Gastronomia": sorted([c for c in cols if c.startswith("fnb_")]),
        "Dział Sprzedaży": sorted([c for c in cols if c.startswith("sprzedaz_")]),
        "Inne Centra": sorted([c for c in cols if c.startswith("inne_")]),
        "Koszty": sorted([c for c in cols if c.startswith("koszt_")]),
    }

def _group_key(group: str) -> str:
    return (group.lower()
            .replace(" ", "_").replace("ł","l").replace("ś","s").replace("ż","z")
            .replace("ź","z").replace("ą","a").replace("ę","e").replace("ó","o")
            .replace("ń","n").replace("ć","c"))

def _filter_missing_rows(df: pd.DataFrame, cols: Iterable[str]) -> pd.DataFrame:
    cols = [c for c in cols if c in df.columns]
    if not cols:
        return df.reset_index(drop=True)
    miss = _is_missing_frame(df[cols])
    mask = miss.any(axis=1)
    return df.loc[mask].reset_index(drop=True)

def _merge_back(original: pd.DataFrame, edited_view: pd.DataFrame) -> pd.DataFrame:
    if edited_view.empty:
        return original.copy()
    base = original.set_index("data")
    patch = edited_view.set_index("data")
    common = [c for c in patch.columns if c in base.columns]
    base.loc[patch.index, common] = patch[common]
    return base.reset_index()

def _style_missing(df_like: pd.DataFrame, *, subset_cols: Optional[Iterable[str]] = None) -> pd.io.formats.style.Styler:
    df = df_like.copy()
    today = pd.to_datetime(date.today())
    if "data" in df.columns:
        df = df[df["data"] <= today]
    cols = [c for c in (subset_cols or REQUIRED_COLS_DEFAULT) if c in df.columns]
    if not cols:
        return df.style
    miss = _is_missing_frame(df[cols])
    def style_subset(subdf: pd.DataFrame) -> pd.DataFrame:
        local = miss.reindex(subdf.index).reindex(columns=subdf.columns, fill_value=False)
        return local.replace({True: "background-color: #ffdddd", False: ""})
    return df.style.apply(style_subset, axis=None, subset=cols)

def _column_config_for(df: pd.DataFrame) -> Dict[str, st.column_config.BaseColumn]:
    cfg: Dict[str, st.column_config.BaseColumn] = {}
    for c in df.columns:
        if c == "data":
            cfg[c] = st.column_config.DateColumn("Data", disabled=True)
            continue
        label = DISPLAY_LABELS.get(c, c)
        if c.endswith("_qty"):
            cfg[c] = st.column_config.NumberColumn(label, step=1.0, format="%.0f")
        elif c.endswith("_pln"):
            cfg[c] = st.column_config.NumberColumn(label, step=1.0, format="%.2f")
        elif c.endswith("_pct"):
            cfg[c] = st.column_config.NumberColumn(label, step=0.01, format="%.2f")
        else:
            cfg[c] = st.column_config.NumberColumn(label, step=1.0, format="%.2f")
    return cfg

# ───── GŁÓWNY RENDER ─────
def render(readonly: bool = False) -> None:
    role = st.session_state.get("role", "GM")
    year = int(st.session_state.get("year", 2025))
    month = int(st.session_state.get("month", 1))
    is_inv = readonly or (role == "INV")

    init_exec_year(year)
    migrate_exec_session()

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

    df_full = get_month_df(year, month)
    df_edit, df_future = split_editable(df_full)

    groups = _detect_groups(df_edit)
    groups["Wszystkie"] = [c for c in df_edit.columns if c != "data"]

    fc1, fc2, fc3 = st.columns([2, 3, 2])
    with fc1:
        only_missing = st.checkbox("Pokaż tylko wiersze nieuzupełnione", value=False, key=f"only_missing_{year}_{month}")
    with fc2:
        group = st.selectbox("Grupa kolumn", list(groups.keys()),
                             index=(list(groups.keys()).index("Pokoje") if "Pokoje" in groups else 0),
                             key=f"group_{year}_{month}")
    with fc3:
        cnt_placeholder = st.empty()

    group_cols = [c for c in groups.get(group, []) if c in df_edit.columns]
    subset_cols_for_style = group_cols or [c for c in REQUIRED_COLS_DEFAULT if c in df_edit.columns]

    view_df = _filter_missing_rows(df_edit, group_cols or subset_cols_for_style) if only_missing else df_edit
    cnt_placeholder.caption(f"Pokazujesz {len(view_df)} z {len(df_edit)} dni")

    st.markdown("#### Dni do dziś")
    if is_inv:
        st.info("Tryb podglądu – edycja wyłączona (INV).")
        st.dataframe(_style_missing(view_df, subset_cols=subset_cols_for_style), width="stretch", hide_index=True)
        all_now = pd.concat([df_edit, df_future], ignore_index=True)
    else:
        cfg = _column_config_for(view_df)
        editor_key = f"editor_{year}_{month}_{_group_key(group)}_{int(only_missing)}"
        edited_view = st.data_editor(view_df, column_config=cfg, num_rows="fixed", width="stretch",
                                     hide_index=True, key=editor_key)

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
            st.dataframe(_style_missing(edited_view, subset_cols=subset_cols_for_style),
                         width="stretch", hide_index=True)

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
                    axis=None, subset=cols,
                )
                st.dataframe(styled, width="stretch", hide_index=True)

        all_now = pd.concat([_merge_back(df_edit, edited_view), df_future], ignore_index=True)

    # Dni przyszłe
    if not df_future.empty:
        st.markdown("#### Dni przyszłe (podgląd)")
        st.dataframe(df_future, width="stretch", hide_index=True)

    # Audit
    st.subheader("Historia zmian (audit log)")
    audit = get_audit(year, month)
    st.write("Brak zmian w tym miesiącu.") if audit.empty else st.dataframe(
        audit.sort_values("czas", ascending=False), width="stretch", hide_index=True
    )

    # ───── KPI (z adapterem do starych nazw) ─────
    all_now_kpi = _to_old_cols_df(all_now)
    exec_state = st.session_state.get("exec", {})
    exec_kpi = _to_old_cols_exec(exec_state)

    st.subheader("Podsumowania KPI")
    r_m = kpi_rooms_month(all_now_kpi)
    f_m = kpi_fnb_month(all_now_kpi)
    r_y = kpi_rooms_ytd(exec_kpi, year, month)
    f_y = kpi_fnb_ytd(exec_kpi, year, month)

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

    # Eksport
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
