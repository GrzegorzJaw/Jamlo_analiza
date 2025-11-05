# src/app.py
from __future__ import annotations

from typing import Dict, List, Tuple, Callable
import pandas as pd
import streamlit as st

# Lokalny stan (pracujemy bez Drive)
from core.state_local import (
    init_exec_year,
    migrate_to_new_schema,
    get_month_df,
)

# ─────────────────────────────────────────────────────────────────────────────
# USTAWIENIA STRONY + UKRYCIE LISTY MULTIPAGE W SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Analiza hotelowa – Departamenty", layout="wide")

# Ukryj wbudowane menu „pages” w sidebarze (arch, covenants, itp.)
st.markdown(
    """
    <style>
    /* ukryj nawigację multipage w sidebarze */
    div[data-testid="stSidebarNav"] { display: none !important; }
    /* drobne odstępy w sidebarze */
    section[data-testid="stSidebar"] { padding-top: 0.5rem !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────────────────────
# POMOCNICZE
# ─────────────────────────────────────────────────────────────────────────────
MONTHS_PL = ["sty", "lut", "mar", "kwi", "maj", "cze", "lip", "sie", "wrz", "paź", "lis", "gru"]

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

# ─────────────────────────────────────────────────────────────────────────────
# AGREGACJE MIESIĘCZNE (POKOJE / F&B / SPRZEDAŻ)
# ─────────────────────────────────────────────────────────────────────────────
def _rooms_month_summary(df: pd.DataFrame) -> Dict[str, float]:
    available = float((_num(df.get("pokoje_dostepne_qty", 0)) - _num(df.get("pokoje_oos_qty", 0))).sum())
    sold = float((_num(df.get("pokoje_sprzedane_bez_qty", 0)) + _num(df.get("pokoje_sprzedane_ze_qty", 0))).sum())
    revenue_rooms = float(_num(df.get("pokoje_przychod_netto_pln", 0)).sum())

    frekw = (sold / available) if available > 0 else 0.0
    revpor = (revenue_rooms / sold) if sold > 0 else 0.0

    koszt_wydzialowe = _sum_prefix(df, "koszt_r_")

    # Koszty osobowe (r_)
    k_os_wyn = _sum_cols(df, ["koszt_r_osobowe_wynagrodzenia_pln"])
    k_os_zus = _sum_cols(df, ["koszt_r_osobowe_zus_pln"])
    k_os_pfr = _sum_cols(df, ["koszt_r_osobowe_pfron_pln"])
    k_os_wyz = _sum_cols(df, ["koszt_r_osobowe_wyzywienie_pln"])
    k_os_bhp = _sum_cols(df, ["koszt_r_osobowe_odziez_bhp_pln"])
    k_os_med = _sum_cols(df, ["koszt_r_osobowe_medyczne_pln"])
    k_os_inn = _sum_cols(df, ["koszt_r_osobowe_inne_pln"])

    # Materiały (r_)
    k_mat_eks = _sum_cols(df, ["koszt_r_materialy_eksplo_spozywcze_pln"])
    k_mat_cos = _sum_cols(df, ["koszt_r_materialy_kosmetyki_czystosc_pln"])
    k_mat_inn = _sum_cols(df, ["koszt_r_materialy_inne_biurowe_pln"])

    # Usługi obce (r_)
    k_usl_sprz = _sum_cols(df, ["koszt_r_uslugi_sprzatanie_pln"])
    k_usl_pran_z = _sum_cols(df, ["koszt_r_uslugi_pranie_zew_pln"])
    k_usl_pran_o = _sum_cols(df, ["koszt_r_uslugi_pranie_odziezy_pln"])
    k_usl_wyn = _sum_cols(df, ["koszt_r_uslugi_wynajem_sprzetu_pln"])
    k_usl_inn = _sum_cols(df, ["koszt_r_uslugi_inne_pln"])

    # Pozostałe (r_)
    k_poz_prow = _sum_cols(df, ["koszt_r_prowizje_ota_gds_pln"])

    return {
        "liczba_pokoi": available,
        "zdolnosc_eksploatacyjna": available,
        "sprzedane_pokojonoce": sold,
        "frekwencja": frekw,
        "revpor": revpor,
        "sprzedaz_pokoi": revenue_rooms,
        "sprzedaz_pokoi_sm": 0.0,  # placeholder
        "koszty_wydzialowe": koszt_wydzialowe,
        # osobowe
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
        # usługi
        "usl_sprzatanie": k_usl_sprz,
        "usl_pranie_zew": k_usl_pran_z,
        "usl_pranie_odziezy_sluzbowej": k_usl_pran_o,
        "usl_wynajem_sprzetu": k_usl_wyn,
        "usl_inne_bhp": k_usl_inn,
        # pozostałe
        "poz_prowizje_ota_gds": k_poz_prow,
        # wynik
        "wynik_departamentu": revenue_rooms - koszt_wydzialowe,
    }

def _fnb_month_summary(df: pd.DataFrame) -> Dict[str, float]:
    r_sni = _sum_cols(df, ["fnb_sniadania_pakietowe_pln"])
    r_kol = _sum_cols(df, ["fnb_kolacje_pakietowe_pln"])
    r_zac = _sum_cols(df, ["fnb_zywnosc_a_la_carte_pln"])
    r_nac = _sum_cols(df, ["fnb_napoje_a_la_carte_pln"])
    r_zbn = _sum_cols(df, ["fnb_zywnosc_bankiety_pln"])
    r_nbn = _sum_cols(df, ["fnb_napoje_bankiety_pln"])
    r_cat = _sum_cols(df, ["fnb_catering_pln"])
    r_sum = r_sni + r_kol + r_zac + r_nac + r_zbn + r_nbn + r_cat

    k_surow_zyw = _sum_cols(df, ["koszt_g_surowiec_zywnosc_pln"])
    k_surow_nap = _sum_cols(df, ["koszt_g_surowiec_napoje_pln"])

    g_os_wyn = _sum_cols(df, ["koszt_g_osobowe_wynagrodzenia_pln"])
    g_os_zus = _sum_cols(df, ["koszt_g_osobowe_zus_pln"])
    g_os_pfr = _sum_cols(df, ["koszt_g_osobowe_pfron_pln"])
    g_os_wyz = _sum_cols(df, ["koszt_g_osobowe_wyzywienie_pln"])
    g_os_bhp = _sum_cols(df, ["koszt_g_osobowe_odziez_bhp_pln"])
    g_os_med = _sum_cols(df, ["koszt_g_osobowe_medyczne_pln"])
    g_os_inn = _sum_cols(df, ["koszt_g_osobowe_inne_pln"])

    g_mat_zas = _sum_cols(df, ["koszt_g_materialy_zastawa_pln"])
    g_mat_drw = _sum_cols(df, ["koszt_g_materialy_drobne_wypos_pln"])
    g_mat_bie = _sum_cols(df, ["koszt_g_materialy_bielizna_dekor_pln"])
    g_mat_kda = _sum_cols(df, ["koszt_g_materialy_karty_dan_pln"])
    g_mat_czy = _sum_cols(df, ["koszt_g_materialy_srodki_czystosci_pln"])
    g_mat_inn = _sum_cols(df, ["koszt_g_materialy_inne_pln"])

    g_usl_sprz = _sum_cols(df, ["koszt_g_uslugi_sprzatanie_pln"])
    g_usl_pran_o = _sum_cols(df, ["koszt_g_uslugi_pranie_odziezy_pln"])
    g_usl_pran_b = _sum_cols(df, ["koszt_g_uslugi_pranie_bielizny_pln"])
    g_usl_wyn = _sum_cols(df, ["koszt_g_uslugi_wynajem_sprzetu_pln"])
    g_usl_inn = _sum_cols(df, ["koszt_g_uslugi_inne_pln"])

    g_koszty = (
        k_surow_zyw + k_surow_nap + g_os_wyn + g_os_zus + g_os_pfr + g_os_wyz + g_os_bhp +
        g_os_med + g_os_inn + g_mat_zas + g_mat_drw + g_mat_bie + g_mat_kda + g_mat_czy +
        g_mat_inn + g_usl_sprz + g_usl_pran_o + g_usl_pran_b + g_usl_wyn + g_usl_inn
    )

    return {
        "sprzedaz_sniadania_pakietowe": r_sni,
        "sprzedaz_kolacje_pakietowe": r_kol,
        "sprzedaz_zywnosc_alacarte": r_zac,
        "sprzedaz_napoje_alacarte": r_nac,
        "sprzedaz_zywnosc_bankiety": r_zbn,
        "sprzedaz_napoje_bankiety": r_nbn,
        "sprzedaz_catering": r_cat,
        "sprzedaz_fnb_suma": r_sum,
        "koszt_surowiec_zywnosc": k_surow_zyw,
        "koszt_surowiec_napoje": k_surow_nap,
        "g_os_wynagrodzenia": g_os_wyn,
        "g_os_zus": g_os_zus,
        "g_os_pfron": g_os_pfr,
        "g_os_wyzywienie": g_os_wyz,
        "g_os_odziez_bhp": g_os_bhp,
        "g_os_medyczne": g_os_med,
        "g_os_inne": g_os_inn,
        "g_mat_zastawa": g_mat_zas,
        "g_mat_drobne": g_mat_drw,
        "g_mat_bielizna_dekor": g_mat_bie,
        "g_mat_karty_dan": g_mat_kda,
        "g_mat_srodki_czystosci": g_mat_czy,
        "g_mat_inne": g_mat_inn,
        "g_usl_sprzatanie": g_usl_sprz,
        "g_usl_pranie_odziezy": g_usl_pran_o,
        "g_usl_pranie_bielizny": g_usl_pran_b,
        "g_usl_wynajem_sprzetu": g_usl_wyn,
        "g_usl_inne": g_usl_inn,
        "fnb_wynik": r_sum - g_koszty,
    }

def _sales_month_summary(df: pd.DataFrame) -> Dict[str, float]:
    wynajem = _sum_cols(df, ["sprzedaz_wynajem_sali_pln"])
    return {"sprzedaz_wynajem_sali": wynajem}

# ─────────────────────────────────────────────────────────────────────────────
# GENERATOR MACIERZY + FORMATY
# ─────────────────────────────────────────────────────────────────────────────
RowSpec = List[Tuple[str, str]]

def _build_matrix(
    year: int,
    rows: RowSpec,
    month_summary_fn: Callable[[pd.DataFrame], Dict[str, float]],
) -> pd.DataFrame:
    months_data: Dict[int, Dict[str, float]] = {}
    for m in range(1, 13):
        df = get_month_df(year, m)
        months_data[m] = month_summary_fn(df)

    mx = pd.DataFrame(
        index=[label for key, label in rows],
        columns=[MONTHS_PL[m - 1] for m in range(1, 13)],
        dtype=float,
    )
    for key, label in rows:
        for m in range(1, 13):
            mx.at[label, MONTHS_PL[m - 1]] = months_data[m].get(key, 0.0)
    return mx

def _format_matrix(matrix: pd.DataFrame, percent_rows: List[str], money_rows: List[str]) -> pd.io.formats.style.Styler:
    def fmt_cell(v, r, c):
        if r in percent_rows:
            return f"{v:.1%}"
        if r in money_rows:
            return f"{v:,.2f}".replace(",", " ").replace(".", ",")
        return f"{v:,.0f}"
    return matrix.style.format(fmt_cell).set_properties(**{"text-align": "right"})

# ─────────────────────────────────────────────────────────────────────────────
# GŁÓWNY EKRAN: ZAKŁADKI
# ─────────────────────────────────────────────────────────────────────────────
def main() -> None:
    # Kontekst globalny (rola/rok/miesiąc są nadal w session_state; rola GM/INV zostaje)
    st.session_state.setdefault("role", "GM")
    st.session_state.setdefault("year", 2025)
    year = int(st.session_state["year"])

    # Dane lokalne – gotowe miesiące + migracja nazw kolumn
    init_exec_year(year)
    migrate_to_new_schema()

    st.header("Departamenty – przegląd (bez lewego menu)")

    tabs = st.tabs(
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

    # POKOJE
    with tabs[0]:
        st.subheader(f"Pokoje – macierz miesięczna ({year})")
        pokoje_rows: RowSpec = [
            ("liczba_pokoi", "liczba pokoi"),
            ("zdolnosc_eksploatacyjna", "zdolność eksploatacyjna"),
            ("sprzedane_pokojonoce", "sprzedane pokojonoce"),
            ("frekwencja", "frekwencja"),
            ("revpor", "średnia cena (RevPOR)"),
            ("sprzedaz_pokoi", "Sprzedaż pokoi"),
            ("sprzedaz_pokoi_sm", "Sprzedaż pokoi S&M"),
            ("koszty_wydzialowe", "Koszty wydziałowe"),
            ("os_wynagrodzenia", "Koszty osobowe • Wynagrodzenie brutto i umowy zlecenia"),
            ("os_zus", "Koszty osobowe • ZUS"),
            ("os_pfron", "Koszty osobowe • PFRON"),
            ("os_wyzywienie", "Koszty osobowe • Wyżywienie"),
            ("os_odziez_bhp", "Koszty osobowe • Odzież służbowa i bhp"),
            ("os_medyczne", "Koszty osobowe • Usługi medyczne"),
            ("os_inne", "Koszty osobowe • Inne"),
            ("mat_eksplo_spozywcze", "Zużycie materiałów • Materiały eksploatacyjne, Artykuły spożywcze"),
            ("mat_kosmetyki_czystosc", "Zużycie materiałów • Kosmetyki (płyn, mydło), Środki czystości 1,5"),
            ("mat_inne_biurowe", "Zużycie materiałów • Inne materiały (karty, galanteria, biurowe 2,5)"),
            ("usl_sprzatanie", "Usługi obce • Usługi sprzątania"),
            ("usl_pranie_zew", "Usługi obce • Usługi prania (z wyłączeniem odzieży służbowej)"),
            ("usl_pranie_odziezy_sluzbowej", "Usługi obce • Usługi prania odzieży służbowej"),
            ("usl_wynajem_sprzetu", "Usługi obce • Wynajem sprzętu (kopiarka, maty, maszyna do butów)"),
            ("usl_inne_bhp", "Usługi obce • Inne usługi (szkolenie BHP)"),
            ("poz_prowizje_ota_gds", "Pozostałe koszty • Prowizje OTA&GDS"),
            ("wynik_departamentu", "WYNIK DEPARTAMENTU"),
        ]
        mx = _build_matrix(year, pokoje_rows, _rooms_month_summary)
        styled = _format_matrix(
            mx,
            percent_rows=["frekwencja"],
            money_rows=[r for _, r in pokoje_rows if r not in ("liczba pokoi", "zdolność eksploatacyjna", "sprzedane pokojonoce", "frekwencja")],
        )
        st.dataframe(styled, width="stretch")

    # GASTRONOMIA
    with tabs[1]:
        st.subheader(f"Gastronomia – macierz miesięczna ({year})")
        fnb_rows: RowSpec = [
            ("sprzedaz_sniadania_pakietowe", "Sprzedaż • Śniadania pakietowe"),
            ("sprzedaz_kolacje_pakietowe", "Sprzedaż • Kolacje / posiłki pakietowe"),
            ("sprzedaz_zywnosc_alacarte", "Sprzedaż • Żywność indywidualna (a la carte)"),
            ("sprzedaz_napoje_alacarte", "Sprzedaż • Napoje indywidualne (a la carte)"),
            ("sprzedaz_zywnosc_bankiety", "Sprzedaż • Żywność bankiety"),
            ("sprzedaz_napoje_bankiety", "Sprzedaż • Napoje bankiety"),
            ("sprzedaz_catering", "Sprzedaż • Catering"),
            ("sprzedaz_fnb_suma", "Sprzedaż gastronomii (suma)"),
            ("koszt_surowiec_zywnosc", "Koszty wydziałowe • Koszt surowca żywność (PLN)"),
            ("koszt_surowiec_napoje", "Koszty wydziałowe • Koszt surowca napoje (PLN)"),
            ("g_os_wynagrodzenia", "Koszty osobowe • Wynagrodzenia brutto i umowy zlecenia"),
            ("g_os_zus", "Koszty osobowe • ZUS"),
            ("g_os_pfron", "Koszty osobowe • PFRON"),
            ("g_os_wyzywienie", "Koszty osobowe • Wyżywienie"),
            ("g_os_odziez_bhp", "Koszty osobowe • Odzież służbowa i bhp"),
            ("g_os_medyczne", "Koszty osobowe • Usługi medyczne"),
            ("g_os_inne", "Koszty osobowe • Inne"),
            ("g_mat_zastawa", "Zużycie materiałów • Zastawa stołowa, szkło, naczynia"),
            ("g_mat_drobne", "Zużycie materiałów • Drobne wyposażenie niskocenne"),
            ("g_mat_bielizna_dekor", "Zużycie materiałów • Bielizna / Dekoracje"),
            ("g_mat_karty_dan", "Zużycie materiałów • Karty dań, rachunki"),
            ("g_mat_srodki_czystosci", "Zużycie materiałów • Środki czystości"),
            ("g_mat_inne", "Zużycie materiałów • Inne materiały"),
            ("g_usl_sprzatanie", "Usługi obce • Usługi sprzątania / tapicerki"),
            ("g_usl_pranie_odziezy", "Usługi obce • Pranie odzieży służbowej"),
            ("g_usl_pranie_bielizny", "Usługi obce • Pranie bielizny gastronomicznej"),
            ("g_usl_wynajem_sprzetu", "Usługi obce • Wynajem sprzętu i lokali"),
            ("g_usl_inne", "Usługi obce • Inne usługi (rozrywkowe/obsługa/szkolenia)"),
            ("fnb_wynik", "WYNIK DEPARTAMENTU F&B"),
        ]
        mx = _build_matrix(year, fnb_rows, _fnb_month_summary)
        styled = _format_matrix(mx, percent_rows=[], money_rows=[r for _, r in fnb_rows])
        st.dataframe(styled, width="stretch")

    # ADMINISTRACJA I DYREKCJA
    with tabs[2]:
        st.info("Widok w przygotowaniu (koszty administracyjne i dyrekcyjne).")

    # DZIAŁ SPRZEDAŻY
    with tabs[3]:
        st.subheader(f"Dział Sprzedaży – macierz miesięczna ({year})")
        sales_rows: RowSpec = [("sprzedaz_wynajem_sali", "Sprzedaż • Wynajem Sali")]
        mx = _build_matrix(year, sales_rows, _sales_month_summary)
        styled = _format_matrix(mx, percent_rows=[], money_rows=[r for _, r in sales_rows])
        st.dataframe(styled, width="stretch")

    # DZIAŁ TECHNICZNY
    with tabs[4]:
        st.info("Widok w przygotowaniu (Tech: media, przeglądy, koszty techniczne).")

    # KOSZTY (2 podzakładki)
    with tabs[5]:
        sub1, sub2 = st.tabs(["Koszty Osobowe", "Koszty stałe"])
        with sub1:
            st.info("Widok 'Koszty Osobowe' – do zasilenia sumami z odpowiednich prefiksów (koszt_*_osobowe_*).")
        with sub2:
            st.info("Widok 'Koszty stałe' – do zasilenia odpowiednimi kategoriami stałymi.")

    # POZOSTAŁE CENTRA
    with tabs[6]:
        st.info("Widok w przygotowaniu (inne przychody i koszty).")


if __name__ == "__main__":
    main()
