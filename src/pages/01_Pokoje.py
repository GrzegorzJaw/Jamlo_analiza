# src/pages/01_Pokoje.py
from __future__ import annotations
import streamlit as st
import pandas as pd

# Jeżeli masz te funkcje – użyj; jeśli nie, strona pokaże pustą macierz (0)
try:
    from core.state_local import get_month_df, init_exec_year, migrate_to_new_schema
except Exception:
    def get_month_df(year: int, month: int) -> pd.DataFrame:  # fallback
        return pd.DataFrame()
    def init_exec_year(year: int): pass
    def migrate_to_new_schema(): pass

MONTHS = ["sty","lut","mar","kwi","maj","cze","lip","sie","wrz","paź","lis","gru"]

# ──────────────────────────────────────────────────────────────────────────────
# DEFINICJA WIERSZY – zgodnie z Twoim arkuszem
# ──────────────────────────────────────────────────────────────────────────────
ROWS = [
    "liczba pokoi",
    "zdolność eksploatacyjna",
    "sprzedane pokojonoce",
    "frekwencja",
    "średnia cena (RevPOR)",

    "— Sprzedaż pokoi —",
    "Sprzedaż pokoi",
    "Sprzedaż pokoi S&M",
    "Koszty wydziałowe",

    "— Koszty osobowe —",
    "Wynagrodzenie brutto i umowy zlecenia",
    "ZUS",
    "PFRON",
    "Wyżywienie",
    "Odzież służbowa i bhp",
    "Usługi medyczne",
    "Inne",

    "— Zużycie materiałów —",
    "Materiały eksploatacyjne, Artykuły spożywcze",
    "Kosmetyki dla gości (płyn, mydło), Środki czystości 1,5",
    "Inne materiały, w tym karty meldunkowe, galanteria papiernicza, art. biurowe",

    "— Usługi obce —",
    "Usługi sprzątania",
    "Usługi prania (z wyłączeniem odzieży służbowej)",
    "Usługi prania odzieży służbowej",
    "Wynajem sprzętu (kopiarka , maty, maszyna do butów )",
    "Inne usługi (szkolenie BHP)",

    "— Pozostałe koszty —",
    "Prowizje OTA&GDS",

    "— WYNIK DEPARTAMENTU —",
    "koszt na sprzedany pokój",
]

# ──────────────────────────────────────────────────────────────────────────────
# PROSTE POMOCNIKI (zostają nawet, jeśli nie podłączysz źródeł od razu)
# ──────────────────────────────────────────────────────────────────────────────
def _num(s: pd.Series | float | int) -> pd.Series:
    return pd.to_numeric(s, errors="coerce").fillna(0.0)

def _find_cols(df: pd.DataFrame, *needles: str):
    """Znajdź kolumny zawierające wszystkie podane frazy (case-insensitive)."""
    if df.empty: return []
    low = {c: c.lower() for c in df.columns}
    out = []
    for c, lc in low.items():
        if all(n in lc for n in needles):
            out.append(c)
    return out

def _sum(df: pd.DataFrame, *needles: str) -> float:
    cols = _find_cols(df, *needles)
    return float(_num(df[cols].stack()).sum()) if cols else 0.0

# ──────────────────────────────────────────────────────────────────────────────
# LICZENIE MIESIĘCZNE – NA RAZIE z heurystyką nazw (możesz podmienić na twarde mapy)
# ──────────────────────────────────────────────────────────────────────────────
def _rooms_month_summary(df: pd.DataFrame) -> dict[str, float]:
    # Ilości / sprzedaż
    available = _sum(df, "pokoje", "do sprzeda") or _sum(df, "pokoje", "dostęp")
    oos       = _sum(df, "oos")
    capacity  = max(available - oos, 0.0)

    sold = (
        _sum(df, "sprzedane", "bez") +
        _sum(df, "sprzedane", "ze")
    )
    revenue_rooms = _sum(df, "przychody", "pokoje") or _sum(df, "sprzedaż", "pokoj")
    sm_revenue    = _sum(df, "sprzedaż", "s&m")  # jeśli wyodrębniasz

    occ = (sold / capacity) if capacity > 0 else 0.0
    revpor = (revenue_rooms / sold) if sold > 0 else 0.0

    # Koszty – placeholdery + heurystyka
    k_wydz   = _sum(df, "koszt", "wydział") or 0.0

    k_wyn    = _sum(df, "koszt", "wynagrodz")
    k_zus    = _sum(df, "zus")
    k_pfron  = _sum(df, "pfron")
    k_wyz    = _sum(df, "wyżyw")
    k_bhp    = _sum(df, "odzie", "bhp")
    k_med    = _sum(df, "medycz")
    k_inneos = _sum(df, "osobowe", "inne")

    k_mat_eks = _sum(df, "materia", "eksplo") or _sum(df, "artykuły", "spożywcze")
    k_mat_kos = _sum(df, "kosmetyki") + _sum(df, "środki", "czystości")
    k_mat_inn = _sum(df, "inne", "materia") + _sum(df, "galanteria") + _sum(df, "biurowe")

    k_usl_sprz = _sum(df, "usługi", "sprząt")
    k_usl_pran = _sum(df, "usługi", "prani") - _sum(df, "odzież", "służbow")  # szacunkowo
    k_usl_pr_odz = _sum(df, "pranie", "odzież")
    k_usl_wyn = _sum(df, "wynajem", "sprzęt")
    k_usl_inne = _sum(df, "szkolen", "bhp") + _sum(df, "usługi", "inne")

    k_prow = _sum(df, "prowizje") + _sum(df, "ota") + _sum(df, "gds")

    wynik = revenue_rooms - (
        k_wydz + k_wyn + k_zus + k_pfron + k_wyz + k_bhp + k_med + k_inneos +
        k_mat_eks + k_mat_kos + k_mat_inn +
        k_usl_sprz + k_usl_pran + k_usl_pr_odz + k_usl_wyn + k_usl_inne +
        k_prow
    )
    koszt_na_sprz = (0.0 if sold <= 0 else (revenue_rooms - wynik) / sold)

    return {
        "liczba pokoi": available,                     # jeśli chcesz mieć „liczbę pokoi stałą” → podmień źródło
        "zdolność eksploatacyjna": capacity,
        "sprzedane pokojonoce": sold,
        "frekwencja": occ,
        "średnia cena (RevPOR)": revpor,

        "Sprzedaż pokoi": revenue_rooms,
        "Sprzedaż pokoi S&M": sm_revenue,
        "Koszty wydziałowe": k_wydz,

        "Wynagrodzenie brutto i umowy zlecenia": k_wyn,
        "ZUS": k_zus,
        "PFRON": k_pfron,
        "Wyżywienie": k_wyz,
        "Odzież służbowa i bhp": k_bhp,
        "Usługi medyczne": k_med,
        "Inne": k_inneos,

        "Materiały eksploatacyjne, Artykuły spożywcze": k_mat_eks,
        "Kosmetyki dla gości (płyn, mydło), Środki czystości 1,5": k_mat_kos,
        "Inne materiały, w tym karty meldunkowe, galanteria papiernicza, art. biurowe": k_mat_inn,

        "Usługi sprzątania": k_usl_sprz,
        "Usługi prania (z wyłączeniem odzieży służbowej)": max(k_usl_pran, 0.0),
        "Usługi prania odzieży służbowej": k_usl_pr_odz,
        "Wynajem sprzętu (kopiarka , maty, maszyna do butów )": k_usl_wyn,
        "Inne usługi (szkolenie BHP)": k_usl_inne,

        "Prowizje OTA&GDS": k_prow,

        "WYNIK DEPARTAMENTU": wynik,
        "koszt na sprzedany pokój": koszt_na_sprz,
    }

def _build_matrix(year: int) -> pd.DataFrame:
    # policz każdy miesiąc
    month_maps: dict[int, dict[str, float]] = {}
    for m in range(1, 13):
        df_m = get_month_df(year, m)
        month_maps[m] = _rooms_month_summary(df_m)

    # zbuduj macierz z domyślnym 0
    mat = pd.DataFrame(0.0, index=ROWS, columns=MONTHS)
    for row in ROWS:
        if row.startswith("—"):     # sekcje – zostaw puste
            mat.loc[row, :] = None
            continue
        for m in range(1, 13):
            mat.loc[row, MONTHS[m-1]] = month_maps[m].get(row, 0.0)
    return mat

# ──────────────────────────────────────────────────────────────────────────────
# UI
# ──────────────────────────────────────────────────────────────────────────────
def render():
    year = int(st.session_state.get("year", 2025))
    init_exec_year(year)
    migrate_to_new_schema()

    st.header(f"Departament POKOJE — {year}")

    matrix = _build_matrix(year)

    # proste formatowanie: % dla frekwencji, 2 miejsca dla PLN, reszta całkowite
    def _fmt(row_name: str, v):
        if row_name == "frekwencja" and pd.notna(v):
            return f"{float(v)*100:,.1f}%".replace(",", " ")
        if row_name.startswith("—") or pd.isna(v):
            return ""
        if row_name in [
            "średnia cena (RevPOR)", "Sprzedaż pokoi", "Sprzedaż pokoi S&M",
            "Koszty wydziałowe", "Wynagrodzenie brutto i umowy zlecenia", "ZUS", "PFRON",
            "Wyżywienie", "Odzież służbowa i bhp", "Usługi medyczne", "Inne",
            "Materiały eksploatacyjne, Artykuły spożywcze",
            "Kosmetyki dla gości (płyn, mydło), Środki czystości 1,5",
            "Inne materiały, w tym karty meldunkowe, galanteria papiernicza, art. biurowe",
            "Usługi sprzątania", "Usługi prania (z wyłączeniem odzieży służbowej)",
            "Usługi prania odzieży służbowej", "Wynajem sprzętu (kopiarka , maty, maszyna do butów )",
            "Inne usługi (szkolenie BHP)", "Prowizje OTA&GDS", "WYNIK DEPARTAMENTU",
            "koszt na sprzedany pokój",
        ]:
            return f"{float(v):,.2f}".replace(",", " ").replace(".", ",")
        return f"{float(v):,.0f}".replace(",", " ")

    # sformatuj do prezentacji (Streamlit nie wspiera w pełni Styler, więc robimy post-proc)
    display = matrix.copy().astype(object)
    for r in display.index:
        for c in display.columns:
            display.at[r, c] = _fmt(r, display.at[r, c])

    st.dataframe(display, use_container_width=True)

# w multipage Streamlit kod pliku jest wykonywany – ale wymuśmy render wprost:
render()
