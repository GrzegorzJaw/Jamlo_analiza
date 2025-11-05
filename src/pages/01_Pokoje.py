# src/pages/01_Pokoje.py
from __future__ import annotations
from typing import Dict, List
import pandas as pd
import streamlit as st

from core.state_local import init_exec_year, migrate_to_new_schema, get_month_df

MONTHS_PL = ["sty", "lut", "mar", "kwi", "maj", "cze", "lip", "sie", "wrz", "paź", "lis", "gru"]


# ──────────────────────────────────────────────────────────────────────────────
# Pomocnicze
# ──────────────────────────────────────────────────────────────────────────────
def _num(s: pd.Series | float | int) -> pd.Series:
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


# ──────────────────────────────────────────────────────────────────────────────
# Agregacje miesięczne – POKOJE
# (podmień mapowania kolumn na Twoje faktyczne nazwy z "Operacje")
# ──────────────────────────────────────────────────────────────────────────────
def _rooms_month_summary(df: pd.DataFrame) -> Dict[str, float]:
    """
    Zwraca słownik wartości dla zakładki 'Pokoje' za dany miesiąc.
    Źródło: dziennik dzienny (Operacje) zwrócony przez get_month_df().
    """
    # Ilości / sprzedaż
    available = float((_num(df.get("pokoje_dostepne_qty", 0)) - _num(df.get("pokoje_oos_qty", 0))).sum())
    sold = float((_num(df.get("pokoje_sprzedane_bez_qty", 0)) + _num(df.get("pokoje_sprzedane_ze_qty", 0))).sum())
    revenue_rooms = float(_num(df.get("pokoje_przychod_netto_pln", 0)).sum())

    frekw = (sold / available) if available > 0 else 0.0
    revpor = (revenue_rooms / sold) if sold > 0 else 0.0

    # Koszty wydziałowe (prefiks dla pokoje – dopasuj do swoich nazw)
    koszt_wydzialowe = _sum_prefix(df, "koszt_r_")

    # Koszty osobowe – rozbicia (dopasuj nazwy kolumn gdy dodasz źródła)
    k_os_wyn = _sum_cols(df, ["koszt_r_osobowe_wynagrodzenia_pln"])
    k_os_zus = _sum_cols(df, ["koszt_r_osobowe_zus_pln"])
    k_os_pfr = _sum_cols(df, ["koszt_r_osobowe_pfron_pln"])
    k_os_wyz = _sum_cols(df, ["koszt_r_osobowe_wyzywienie_pln"])
    k_os_bhp = _sum_cols(df, ["koszt_r_osobowe_odziez_bhp_pln"])
    k_os_med = _sum_cols(df, ["koszt_r_osobowe_medyczne_pln"])
    k_os_inn = _sum_cols(df, ["koszt_r_osobowe_inne_pln"])

    # Zużycie materiałów (pokoje)
    k_mat_eks = _sum_cols(df, ["koszt_r_materialy_eksplo_spozywcze_pln"])
    k_mat_kos = _sum_cols(df, ["koszt_r_materialy_kosmetyki_czystosc_pln"])
    k_mat_inn = _sum_cols(df, ["koszt_r_materialy_inne_biurowe_pln"])

    # Usługi obce (pokoje)
    k_usl_sprz = _sum_cols(df, ["koszt_r_uslugi_sprzatanie_pln"])
    k_usl_pran = _sum_cols(df, ["koszt_r_uslugi_pranie_pln"])  # zewnętrzne + odzież służbowa – rozbijesz później
    k_usl_pran_odz = _sum_cols(df, ["koszt_r_uslugi_pranie_odziezy_pln"])
    k_usl_wyn = _sum_cols(df, ["koszt_r_uslugi_wynajem_sprzetu_pln"])
    k_usl_inne = _sum_cols(df, ["koszt_r_uslugi_inne_pln"])    # np. szkolenia BHP

    # Pozostałe
    k_prow_ota = _sum_cols(df, ["koszt_r_prowizje_ota_gds_pln"])

    return {
        # BLOK: narastająco / główne KPI
        "Ilość pokoi": available,                        # placeholder = dostępne – OOS; rozdzielisz jeśli chcesz
        "zdolność eksploatacyjna": available,            # jw.
        "sprzedane pokojonoce": sold,
        "frekwencja (%)": frekw,                         # % – format w UI
        "średnia cena (RevPOR)": revpor,
        "Sprzedaż pokoi 701/0111; 0112": revenue_rooms,  # przychody pokoi (netto)

        # BLOK: koszty wydziałowe
        "Koszty wydziałowe": koszt_wydzialowe,

        # BLOK: koszty osobowe (szczegół)
        "Wynagrodzenie brutto i umowy zlecenia 701/0101; 201100; ZUS 701/0102": k_os_wyn + k_os_zus,
        "PFRON 701/010102": k_os_pfr,
        "Wyżywienie 701/010104": k_os_wyz,
        "Odzież służbowa i BHP 701/0107; 201902": k_os_bhp,
        "Usługi medyczne 701/0109": k_os_med,
        "Inne osobowe 701/010199": k_os_inn,

        # BLOK: zużycie materiałów
        "Materiały eksploatacyjne, Artykuły spożywcze": k_mat_eks,
        "Kosmetyki dla gości, środki czystości": k_mat_kos,
        "Inne materiały (karty meldunkowe, art. biurowe)": k_mat_inn,

        # BLOK: usługi obce
        "Usługi sprzątania 701/02102": k_usl_sprz,
        "Usługi prania (z wyłączeniem odzieży służbowej) 701/02105": k_usl_pran,
        "Usługi prania odzieży służbowej 701/02107": k_usl_pran_odz,
        "Wynajem sprzętu (kopiarka, maty, maszyna do butów)": k_usl_wyn,
        "Inne usługi (szkolenia BHP)": k_usl_inne,

        # BLOK: pozostałe koszty
        "Prowizje OTA&GDS": k_prow_ota,

        # WYNIK
        "WYNIK DEPARTAMENTU": revenue_rooms - koszt_wydzialowe,  # na razie sprzedaż - koszty wydziałowe
    }


def _build_matrix(year: int) -> pd.DataFrame:
    """Tabela: wiersze jak w arkuszu, kolumny = 12 mies."""
    rows_order = [
        # sekcje nagłówkowe z arkusza pomijamy – same pozycje
        "Ilość pokoi",
        "zdolność eksploatacyjna",
        "sprzedane pokojonoce",
        "frekwencja (%)",
        "średnia cena (RevPOR)",
        "Sprzedaż pokoi 701/0111; 0112",
        "Koszty wydziałowe",
        "Wynagrodzenie brutto i umowy zlecenia 701/0101; 201100; ZUS 701/0102",
        "PFRON 701/010102",
        "Wyżywienie 701/010104",
        "Odzież służbowa i BHP 701/0107; 201902",
        "Usługi medyczne 701/0109",
        "Inne osobowe 701/010199",
        "Materiały eksploatacyjne, Artykuły spożywcze",
        "Kosmetyki dla gości, środki czystości",
        "Inne materiały (karty meldunkowe, art. biurowe)",
        "Usługi sprzątania 701/02102",
        "Usługi prania (z wyłączeniem odzieży służbowej) 701/02105",
        "Usługi prania odzieży służbowej 701/02107",
        "Wynajem sprzętu (kopiarka, maty, maszyna do butów)",
        "Inne usługi (szkolenia BHP)",
        "Prowizje OTA&GDS",
        "WYNIK DEPARTAMENTU",
    ]

    # policz miesiące
    month_summaries: Dict[int, Dict[str, float]] = {}
    for m in range(1, 13):
        df_m = get_month_df(year, m)
        month_summaries[m] = _rooms_month_summary(df_m)

    # zbuduj macierz
    mat = pd.DataFrame(index=rows_order, columns=[MONTHS_PL[m-1] for m in range(1, 13)], dtype=float)
    for row in rows_order:
        for m in range(1, 13):
            mat.at[row, MONTHS_PL[m-1]] = month_summaries[m].get(row, 0.0)

    return mat


# ──────────────────────────────────────────────────────────────────────────────
# UI
# ──────────────────────────────────────────────────────────────────────────────
def _format_money(x: float) -> str:
    return f"{x:,.2f}".replace(",", " ").replace(".", ",")

def _format_int(x: float) -> str:
    return f"{x:,.0f}"

def render() -> None:
    year = int(st.session_state.get("year", 2025))

    init_exec_year(year)
    migrate_to_new_schema()

    st.header(f"Pokoje – podsumowania miesięczne ({year})")

    matrix = _build_matrix(year)

    # formaty wierszy
    fmt_map = {}
    for r in matrix.index:
        if "frekwencja" in r:
            fmt_map[r] = "{:.1%}".format
        elif "RevPOR" in r or "Sprzedaż" in r or "Koszt" in r or "WYNIK" in r or "Prowizje" in r:
            fmt_map[r] = _format_money
        else:
            fmt_map[r] = _format_int

    styled = matrix.style.format(formatter=fmt_map).set_properties(**{"text-align": "right"})
    st.dataframe(styled, use_container_width=True)
