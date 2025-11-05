# src/pages/rooms.py
from __future__ import annotations

from typing import Dict, List
import numpy as np
import pandas as pd
import streamlit as st

from core.state_local import (
    init_exec_year,
    migrate_to_new_schema,
    get_month_df,
)

MONTHS_PL = ["sty", "lut", "mar", "kwi", "maj", "cze", "lip", "sie", "wrz", "paź", "lis", "gru"]


# ──────────────────────────────────────────────────────────────────────────────
# Agregacje miesięczne • POKOJE
# ──────────────────────────────────────────────────────────────────────────────
def _num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce").fillna(0.0)

def _sum_cols(df: pd.DataFrame, cols: List[str]) -> float:
    cols = [c for c in cols if c in df.columns]
    if not cols:
        return 0.0
    return float(_num(df[cols].stack()).sum())

def _sum_prefix(df: pd.DataFrame, prefix: str) -> float:
    cols = [c for c in df.columns if c.startswith(prefix)]
    if not cols:
        return 0.0
    return float(_num(df[cols].stack()).sum())

def _rooms_month_summary(df: pd.DataFrame) -> Dict[str, float]:
    """Zwraca słownik wartości dla zakładki 'Pokoje' za dany miesiąc."""
    # Ilości
    available = float((_num(df.get("pokoje_dostepne_qty", 0)) - _num(df.get("pokoje_oos_qty", 0))).sum())
    sold = float((_num(df.get("pokoje_sprzedane_bez_qty", 0)) + _num(df.get("pokoje_sprzedane_ze_qty", 0))).sum())
    revenue_rooms = float(_num(df.get("pokoje_przychod_netto_pln", 0)).sum())

    frekw = (sold / available) if available > 0 else 0.0
    revpor = (revenue_rooms / sold) if sold > 0 else 0.0

    # Koszty (wydziałowe pokoje) – wszystkie 'koszt_r_*'
    koszt_wydzialowe = _sum_prefix(df, "koszt_r_")

    # Rozbicia kosztów osobowych (r_)
    k_os_wyn = _sum_cols(df, ["koszt_r_osobowe_wynagrodzenia_pln"])
    k_os_zus = _sum_cols(df, ["koszt_r_osobowe_zus_pln"])
    k_os_pfr = _sum_cols(df, ["koszt_r_osobowe_pfron_pln"])
    k_os_wyz = _sum_cols(df, ["koszt_r_osobowe_wyzywienie_pln"])
    k_os_bhp = _sum_cols(df, ["koszt_r_osobowe_odziez_bhp_pln"])
    k_os_med = _sum_cols(df, ["koszt_r_osobowe_medyczne_pln"])
    k_os_inn = _sum_cols(df, ["koszt_r_osobowe_inne_pln"])

    # Materiały (pokoje)
    k_mat_eks = _sum_cols(df, ["koszt_r_materialy_eksplo_spozywcze_pln"])
    k_mat_cos = _sum_cols(df, ["koszt_r_materialy_kosmetyki_czystosc_pln"])
    k_mat_inn = _sum_cols(df, ["koszt_r_materialy_inne_biurowe_pln"])

    # Usługi obce (pokoje)
    k_usl_sprz = _sum_cols(df, ["koszt_r_uslugi_sprzatanie_pln"])
    k_usl_pran_z = _sum_cols(df, ["koszt_r_uslugi_pranie_zew_pln"])
    k_usl_pran_o = _sum_cols(df, ["koszt_r_uslugi_pranie_odziezy_pln"])
    k_usl_wyn = _sum_cols(df, ["koszt_r_uslugi_wynajem_sprzetu_pln"])
    k_usl_inn = _sum_cols(df, ["koszt_r_uslugi_inne_pln"])

    # Pozostałe
    k_poz_prow = _sum_cols(df, ["koszt_r_prowizje_ota_gds_pln"])

    return {
        "liczba_pokoi": available,                    # zgodnie z ustaleniem
        "zdolnosc_eksploatacyjna": available,         # można rozdzielić w przyszłości
        "sprzedane_pokojonoce": sold,
        "frekwencja": frekw,
        "revpor": revpor,
        "sprzedaz_pokoi": revenue_rooms,
        "sprzedaz_pokoi_sm": 0.0,                     # brak źródła – placeholder
        "koszty_wydzialowe": koszt_wydzialowe,
        # koszty osobowe
        "os_wynagrodzenia": k_os_wyn,
        "os_zus": k_os_zus,
        "os_pfron": k_os_pfr,
        "os_wyzywienie": k_os_wyz,
        "os_odziez_bhp": k_os_bhp,
        "os_medyczne": k_os_med,
        "os_inne": k_os_inn,
        # materiały
        "mat_eksplo_spozywcze": k_mat_eks,
        "mat_kosmetyki_czystosc": k_mat_cos,
        "mat_inne_biurowe": k_mat_inn,
        # usługi obce
        "usl_sprzatanie": k_usl_sprz,
        "usl_pranie_zew": k_usl_pran_z,
        "usl_pranie_odziezy_sluzbowej": k_usl_pran_o,
        "usl_wynajem_sprzetu": k_usl_wyn,
        "usl_inne_bhp": k_usl_inn,
        # pozostałe
        "poz_prowizje_ota_gds": k_poz_prow,
        # wynik (można liczć osobno; tu tylko sprzedaż – koszty wydziałowe)
        "wynik_departamentu": revenue_rooms - koszt_wydzialowe,
    }


def _build_rooms_matrix(year: int) -> pd.DataFrame:
    """Zwraca tabelę: wiersze wg specyfikacji, kolumny = 12 miesięcy."""
    # Kolejność i etykiety wierszy
    rows = [
        ("liczba_pokoi", "liczba pokoi"),
        ("zdolnosc_eksploatacyjna", "zdolność eksploatacyjna"),
        ("sprzedane_pokojonoce", "sprzedane pokojonoce"),
        ("frekwencja", "frekwencja"),
        ("revpor", "średnia cena (RevPOR)"),
        ("sprzedaz_pokoi", "Sprzedaż pokoi"),
        ("sprzedaz_pokoi_sm", "Sprzedaż pokoi S&M"),
        ("koszty_wydzialowe", "Koszty wydziałowe"),
        # sekcja: Koszty osobowe
        ("os_wynagrodzenia", "Koszty osobowe • Wynagrodzenie brutto i umowy zlecenia"),
        ("os_zus",            "Koszty osobowe • ZUS"),
        ("os_pfron",          "Koszty osobowe • PFRON"),
        ("os_wyzywienie",     "Koszty osobowe • Wyżywienie"),
        ("os_odziez_bhp",     "Koszty osobowe • Odzież służbowa i bhp"),
        ("os_medyczne",       "Koszty osobowe • Usługi medyczne"),
        ("os_inne",           "Koszty osobowe • Inne"),
        # sekcja: Zużycie materiałów
        ("mat_eksplo_spozywcze",   "Zużycie materiałów • Materiały eksploatacyjne, Artykuły spożywcze"),
        ("mat_kosmetyki_czystosc", "Zużycie materiałów • Kosmetyki dla gości (płyn, mydło), Środki czystości 1,5"),
        ("mat_inne_biurowe",       "Zużycie materiałów • Inne materiały, karty meldunkowe, galanteria, art. biurowe 2,5"),
        # sekcja: Usługi obce
        ("usl_sprzatanie",               "Usługi obce • Usługi sprzątania"),
        ("usl_pranie_zew",               "Usługi obce • Usługi prania (z wyłączeniem odzieży służbowej)"),
        ("usl_pranie_odziezy_sluzbowej", "Usługi obce • Usługi prania odzieży służbowej"),
        ("usl_wynajem_sprzetu",          "Usługi obce • Wynajem sprzętu (kopiarka, maty, maszyna do butów)"),
        ("usl_inne_bhp",                 "Usługi obce • Inne usługi (szkolenie BHP)"),
        # sekcja: Pozostałe koszty
        ("poz_prowizje_ota_gds", "Pozostałe koszty • Prowizje OTA&GDS"),
        # wynik
        ("wynik_departamentu", "WYNIK DEPARTAMENTU"),
    ]

    # Zbierz miesięczne wyniki
    months_data: Dict[int, Dict[str, float]] = {}
    for m in range(1, 13):
        df = get_month_df(year, m)
        months_data[m] = _rooms_month_summary(df)

    # Zbuduj macierz
    matrix = pd.DataFrame(
        index=[label for key, label in rows],
        columns=[f"{MONTHS_PL[m-1]}" for m in range(1, 13)],
        dtype=float,
    )

    for idx_key, idx_label in rows:
        for m in range(1, 13):
            val = months_data[m].get(idx_key, 0.0)
            # formaty: frekwencja i revpor w jednostkach – zapisujemy liczby, formatujemy w UI
            matrix.at[idx_label, f"{MONTHS_PL[m-1]}"] = val

    return matrix


# ──────────────────────────────────────────────────────────────────────────────
# UI
# ──────────────────────────────────────────────────────────────────────────────
def render() -> None:
    # Kontekst globalny
    role = st.session_state.get("role", "GM")
    year = int(st.session_state.get("year", 2025))

    init_exec_year(year)
    migrate_to_new_schema()

    st.header("Departamenty – przegląd")
    main_tabs = st.tabs(
        [
            "Pokoje",
            "Gastronomia",
            "Administracja i Dyrekcja",
            "Dział Sprzedaży",
            "Dział Techniczny",
            "Koszty",
            "Pozostałe Centra",
        ]
    )

    # ── POKOJE
    with main_tabs[0]:
        st.subheader(f"Pokoje – macierz miesięczna ({year})")
        matrix = _build_rooms_matrix(year)

        # Prezentacja – formaty
        fmt = {}
        # % dla frekwencji – rozpoznaj wiersz
        for r in matrix.index:
            if "frekwencja" in r:
                fmt[r] = "{:.1%}".format
            elif "RevPOR" in r or "sprzedaż" in r.lower() or "koszt" in r.lower() or "WYNIK" in r:
                fmt[r] = lambda x: f"{x:,.2f}".replace(",", " ").replace(".", ",")
            else:
                fmt[r] = lambda x: f"{x:,.0f}"

        styled = matrix.style.format(formatter=fmt).set_properties(**{"text-align": "right"})
        st.dataframe(styled, width="stretch")

    # ── GASTRONOMIA
    with main_tabs[1]:
        st.info("Widok w przygotowaniu. Dane będą zasilane sumami miesięcznymi z dziennika Wykonanie (prefiks fnb_ oraz koszt_g_).")

    # ── ADMINISTRACJA I DYREKCJA
    with main_tabs[2]:
        st.info("Widok w przygotowaniu (koszty administracyjne i dyrekcyjne).")

    # ── DZIAŁ SPRZEDAŻY
    with main_tabs[3]:
        st.info("Widok w przygotowaniu (sprzedaż: wynajem sal itp.).")

    # ── DZIAŁ TECHNICZNY
    with main_tabs[4]:
        st.info("Widok w przygotowaniu (Tech: media, przeglądy, koszty techniczne).")

    # ── KOSZTY (podzakładki)
    with main_tabs[5]:
        sub1, sub2 = st.tabs(["Koszty Osobowe", "Koszty stałe"])
        with sub1:
            st.info("Widok 'Koszty Osobowe' – do zasilenia sumami z prefiksów koszt_*_osobowe_*.")
        with sub2:
            st.info("Widok 'Koszty stałe' – do zasilenia odpowiednimi kategoriami stałymi.")

    # ── POZOSTAŁE CENTRA
    with main_tabs[6]:
        st.info("Widok w przygotowaniu (inne przychody i koszty).")
