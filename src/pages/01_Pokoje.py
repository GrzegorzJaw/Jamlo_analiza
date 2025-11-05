# src/pages/01_Pokoje.py
from __future__ import annotations

import pandas as pd
import streamlit as st

# Spróbuj użyć Twoich helperów; jeśli ich nie ma, działamy na fallbacku
try:
    from core.state_local import get_month_df, init_exec_year, migrate_to_new_schema
except Exception:
    def get_month_df(year: int, month: int) -> pd.DataFrame:  # fallback
        return pd.DataFrame()
    def init_exec_year(year: int):  # noqa: D401
        pass
    def migrate_to_new_schema():  # noqa: D401
        pass

MONTHS = ["sty", "lut", "mar", "kwi", "maj", "cze", "lip", "sie", "wrz", "paź", "lis", "gru"]

# ======= DEFINICJA WIERSZY (jak w przekazanym arkuszu) =======
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

# ======= MAPA KOLUMN Z „Operacji” (dopasuj nazwy gdy będzie potrzeba) =======
COLUMN_MAP = {
    # Ilości / sprzedaż / przychód
    "pokoje_do_sprzedazy": "Pokoje do sprzedaży",
    "pokoje_oos": "Pokoje OOS",
    "sprzedane_bez": "Sprzedane BEZ śn.",
    "sprzedane_ze": "Sprzedane ZE śn.",
    "przychody_pokoje": "Przychody pokoje (netto)",

    # Sprzedaż S&M (jeżeli rozdzielasz – inaczej zostanie 0)
    "sprzedaz_sm": "Sprzedaż pokoi S&M (netto)",

    # Koszty osobowe
    "k_os_wyn": "Koszty osobowe – Wynagrodzenia (PLN)",
    "k_os_zus": "Koszty osobowe – ZUS (PLN)",
    "k_os_pfr": "Koszty osobowe – PFRON (PLN)",
    "k_os_wyz": "Koszty osobowe – Wyżywienie (PLN)",
    "k_os_bhp": "Koszty osobowe – Odzież/BHP (PLN)",
    "k_os_med": "Koszty osobowe – Usługi medyczne (PLN)",
    "k_os_inn": "Koszty osobowe – Inne (PLN)",

    # Zużycie materiałów
    "k_mat_eks": "Materiały eksploatacyjne, Artykuły spożywcze (PLN)",
    "k_mat_kos": "Kosmetyki/Środki czystości (PLN)",
    "k_mat_inn": "Inne materiały (PLN)",

    # Usługi obce
    "k_usl_sprz": "Usługi sprzątania (PLN)",
    "k_usl_pran": "Usługi prania (PLN)",
    "k_usl_pran_odz": "Usługi prania odzieży służbowej (PLN)",
    "k_usl_wyn": "Wynajem sprzętu (PLN)",
    "k_usl_inne": "Inne usługi (BHP itd.) (PLN)",

    # Pozostałe
    "k_prow_ota": "Prowizje OTA&GDS (PLN)",

    # Koszty wydziałowe – jeśli masz osobne pole; inaczej licz je jako suma bloków kosztowych
    "k_wydzialowe": "Koszty wydziałowe – Pokoje (PLN)",
}

# ======= POMOCNICZE =======
def _num(s) -> pd.Series:
    return pd.to_numeric(s, errors="coerce").fillna(0.0)

def _col(df: pd.DataFrame, key: str) -> pd.Series:
    name = COLUMN_MAP.get(key)
    if not name or name not in df.columns:
        return pd.Series([], dtype="float64")
    return _num(df[name])

def _month_from_exec(year: int, month: int) -> pd.DataFrame:
    """Dziennik Operacje z sesji, przefiltrowany do YYYY-MM; pusty gdy brak."""
    exec_df = st.session_state.get("exec")
    if exec_df is None or len(exec_df) == 0:
        return pd.DataFrame()
    df = exec_df.copy()
    date_col = "Data" if "Data" in df.columns else ("data" if "data" in df.columns else None)
    if not date_col:
        return pd.DataFrame()
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df[(df[date_col].dt.year == year) & (df[date_col].dt.month == month)]
    return df

# ======= LICZENIE JEDNEGO MIESIĄCA =======
def _rooms_month_summary(df: pd.DataFrame) -> dict[str, float]:
    # Ilości / sprzedaż
    available = float((_col(df, "pokoje_do_sprzedazy") - _col(df, "pokoje_oos")).sum())
    sold = float((_col(df, "sprzedane_bez") + _col(df, "sprzedane_ze")).sum())
    revenue_rooms = float(_col(df, "przychody_pokoje").sum())
    revenue_sm = float(_col(df, "sprzedaz_sm").sum())

    occ = (sold / available) if available > 0 else 0.0
    revpor = (revenue_rooms / sold) if sold > 0 else 0.0

    # Koszty – jeśli brak osobnego pola „wydziałowe”, zostaw 0 i policzymy z bloków
    k_wydz = float(_col(df, "k_wydzialowe").sum()) if COLUMN_MAP.get("k_wydzialowe") else 0.0

    k_os_wyn = float(_col(df, "k_os_wyn").sum())
    k_os_zus = float(_col(df, "k_os_zus").sum())
    k_os_pfr = float(_col(df, "k_os_pfr").sum())
    k_os_wyz = float(_col(df, "k_os_wyz").sum())
    k_os_bhp = float(_col(df, "k_os_bhp").sum())
    k_os_med = float(_col(df, "k_os_med").sum())
    k_os_inn = float(_col(df, "k_os_inn").sum())

    k_mat_eks = float(_col(df, "k_mat_eks").sum())
    k_mat_kos = float(_col(df, "k_mat_kos").sum())
    k_mat_inn = float(_col(df, "k_mat_inn").sum())

    k_usl_sprz = float(_col(df, "k_usl_sprz").sum())
    k_usl_pran = float(_col(df, "k_usl_pran").sum())
    k_usl_pran_odz = float(_col(df, "k_usl_pran_odz").sum())
    k_usl_wyn = float(_col(df, "k_usl_wyn").sum())
    k_usl_inne = float(_col(df, "k_usl_inne").sum())

    k_prow = float(_col(df, "k_prow_ota").sum())

    sum_koszt_blokow = (
        k_os_wyn + k_os_zus + k_os_pfr + k_os_wyz + k_os_bhp + k_os_med + k_os_inn +
        k_mat_eks + k_mat_kos + k_mat_inn +
        k_usl_sprz + k_usl_pran + k_usl_pran_odz + k_usl_wyn + k_usl_inne +
        k_prow
    )
    # Jeśli nie masz „wydziałowe” osobno – potraktuj je jako sumę bloków
    if k_wydz == 0.0:
        k_wydz = sum_koszt_blokow

    wynik = revenue_rooms - k_wydz
    koszt_na_sprz = 0.0 if sold <= 0 else (k_wydz / sold)

    return {
        "liczba pokoi": available,                 # w razie czego podmienisz na stałą liczbę pokoi
        "zdolność eksploatacyjna": available,      # lub capacity (available - OOS); ustaw zgodnie z polityką
        "sprzedane pokojonoce": sold,
        "frekwencja": occ,
        "średnia cena (RevPOR)": revpor,

        "Sprzedaż pokoi": revenue_rooms,
        "Sprzedaż pokoi S&M": revenue_sm,
        "Koszty wydziałowe": k_wydz,

        "Wynagrodzenie brutto i umowy zlecenia": k_os_wyn,
        "ZUS": k_os_zus,
        "PFRON": k_os_pfr,
        "Wyżywienie": k_os_wyz,
        "Odzież służbowa i bhp": k_os_bhp,
        "Usługi medyczne": k_os_med,
        "Inne": k_os_inn,

        "Materiały eksploatacyjne, Artykuły spożywcze": k_mat_eks,
        "Kosmetyki dla gości (płyn, mydło), Środki czystości 1,5": k_mat_kos,
        "Inne materiały, w tym karty meldunkowe, galanteria papiernicza, art. biurowe": k_mat_inn,

        "Usługi sprzątania": k_usl_sprz,
        "Usługi prania (z wyłączeniem odzieży służbowej)": k_usl_pran,
        "Usługi prania odzieży służbowej": k_usl_pran_odz,
        "Wynajem sprzętu (kopiarka , maty, maszyna do butów )": k_usl_wyn,
        "Inne usługi (szkolenie BHP)": k_usl_inne,

        "Prowizje OTA&GDS": k_prow,

        "WYNIK DEPARTAMENTU": wynik,
        "koszt na sprzedany pokój": koszt_na_sprz,
    }

# ======= BUDOWA MACIERZY 12×N =======
def _build_matrix(year: int) -> pd.DataFrame:
    months_data: dict[int, dict[str, float]] = {}
    for m in range(1, 13):
        df_m = get_month_df(year, m)
        if df_m is None or df_m.empty:
            df_m = _month_from_exec(year, m)
        months_data[m] = _rooms_month_summary(df_m)

    mat = pd.DataFrame(0.0, index=ROWS, columns=MONTHS, dtype=float)
    for r in ROWS:
        if r.startswith("—"):
            mat.loc[r, :] = None
            continue
        for m in range(1, 13):
            mat.loc[r, MONTHS[m-1]] = months_data[m].get(r, 0.0)
    return mat

# ======= FORMATOWANIE =======
def _format_cell(row_name: str, v):
    if pd.isna(v) or row_name.startswith("—"):
        return ""
    if row_name == "frekwencja":
        return f"{float(v)*100:,.1f}%".replace(",", " ")
    # PLN – wartości pieniężne
    money_rows = {
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
    }
    if row_name in money_rows:
        return f"{float(v):,.2f}".replace(",", " ").replace(".", ",")
    # ilości/całkowite
    return f"{float(v):,.0f}".replace(",", " ")

# ======= UI =======
def render() -> None:
    year = int(st.session_state.get("year", 2025))
    init_exec_year(year)
    migrate_to_new_schema()

    st.header(f"Departament POKOJE — {year}")

    matrix = _build_matrix(year)

    # jeśli brak danych w ogóle – pokaż informację i pusty szablon
    if matrix.replace(0.0, pd.NA).dropna(how="all").empty:
        st.info("Brak danych z „Operacji” dla wybranego roku. Poniżej szablon tabeli.")
    display = matrix.copy().astype(object)
    for r in display.index:
        for c in display.columns:
            display.at[r, c] = _format_cell(r, display.at[r, c])

    st.dataframe(display, use_container_width=True)

# multipage Streamlit – wykonaj od razu
render()
