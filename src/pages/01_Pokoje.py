# src/pages/01_Pokoje.py
from __future__ import annotations

import pandas as pd
import streamlit as st

# Jeżeli masz helpery – użyj ich; w innym wypadku działamy fallbackiem
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

# ======= WIERSZE wg arkusza =======
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

# ======= Nazwy kolumn w „Operacjach” (dziennik w sesji) – dopasuj gdy trzeba =======
COL = {
    "date": "Data",
    "available": "Pokoje do sprzedaży",
    "oos": "Pokoje OOS",
    "sold_bez": "Sprzedane BEZ śn.",
    "sold_ze": "Sprzedane ZE śn.",
    "revenue_rooms": "Przychody pokoje (netto)",  # używane tylko do sanity-check; właściwy przychód liczony jako sold*RevPOR
    # dodatkowo jeśli masz sprzedaż S&M:
    "sales_sm": "Sprzedaż pokoi S&M (netto)",
}

# ======= Fallback: wyciągnij miesiąc z sesji (Operacje) =======
def _month_from_exec(year: int, month: int) -> pd.DataFrame:
    exec_df = st.session_state.get("exec")
    if exec_df is None or len(exec_df) == 0:
        return pd.DataFrame()
    df = exec_df.copy()
    date_col = COL["date"] if COL["date"] in df.columns else None
    if not date_col:
        return pd.DataFrame()
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df[(df[date_col].dt.year == year) & (df[date_col].dt.month == month)]
    return df

def _n(s) -> pd.Series:
    return pd.to_numeric(s, errors="coerce").fillna(0.0)

# ======= Liczenie KPI miesięcznych (jak w „Podsumowania KPI”) =======
def _kpi_month(df: pd.DataFrame) -> dict[str, float]:
    if df is None or df.empty:
        return dict(available=0.0, sold=0.0, occ=0.0, revpor=0.0, sm=0.0)

    av = _n(df.get(COL["available"], 0)).sum()
    oos = _n(df.get(COL["oos"], 0)).sum()
    capacity = max(av - oos, 0.0)

    sold = (_n(df.get(COL["sold_bez"], 0)) + _n(df.get(COL["sold_ze"], 0))).sum()

    # Jeśli masz bezpośrednio przychód pokoi – można policzyć RevPOR = revenue/sold.
    revenue_rooms = _n(df.get(COL["revenue_rooms"], 0)).sum()
    revpor = (revenue_rooms / sold) if sold > 0 else 0.0
    occ = (sold / capacity) if capacity > 0 else 0.0

    sm = _n(df.get(COL["sales_sm"], 0)).sum() if COL.get("sales_sm") in df.columns else 0.0

    return dict(available=capacity, sold=sold, occ=occ, revpor=revpor, sm=sm)

# ======= Macierz 12×N + integracja z edytowalną „liczbą pokoi” =======
def _build_matrix(year: int, rooms_static: float) -> pd.DataFrame:
    months: dict[int, dict[str, float]] = {}
    for m in range(1, 13):
        df_m = get_month_df(year, m)
        if df_m is None or df_m.empty:
            df_m = _month_from_exec(year, m)
        months[m] = _kpi_month(df_m)

    mat = pd.DataFrame(0.0, index=ROWS, columns=MONTHS, dtype=float)

    for m in range(1, 13):
        col = MONTHS[m-1]
        k = months[m]

        # KPI z Operacji
        capacity = float(k["available"])
        sold = float(k["sold"])
        occ = float(k["occ"])
        revpor = float(k["revpor"])
        sm = float(k["sm"])

        # „Sprzedaż pokoi” zgodnie z Twoją dyrektywą: sold * RevPOR
        sales_rooms = sold * revpor

        # wypełnienie
        mat.at["liczba pokoi", col] = rooms_static
        mat.at["zdolność eksploatacyjna", col] = capacity
        mat.at["sprzedane pokojonoce", col] = sold
        mat.at["frekwencja", col] = occ
        mat.at["średnia cena (RevPOR)", col] = revpor

        mat.at["Sprzedaż pokoi", col] = sales_rooms
        mat.at["Sprzedaż pokoi S&M", col] = sm
        mat.at["Koszty wydziałowe", col] = 0.0  # dopniesz źródło później

        # koszty – placeholdery 0.0 do czasu podpięcia źródeł
        mat.at["Wynagrodzenie brutto i umowy zlecenia", col] = 0.0
        mat.at["ZUS", col] = 0.0
        mat.at["PFRON", col] = 0.0
        mat.at["Wyżywienie", col] = 0.0
        mat.at["Odzież służbowa i bhp", col] = 0.0
        mat.at["Usługi medyczne", col] = 0.0
        mat.at["Inne", col] = 0.0

        mat.at["Materiały eksploatacyjne, Artykuły spożywcze", col] = 0.0
        mat.at["Kosmetyki dla gości (płyn, mydło), Środki czystości 1,5", col] = 0.0
        mat.at["Inne materiały, w tym karty meldunkowe, galanteria papiernicza, art. biurowe", col] = 0.0

        mat.at["Usługi sprzątania", col] = 0.0
        mat.at["Usługi prania (z wyłączeniem odzieży służbowej)", col] = 0.0
        mat.at["Usługi prania odzieży służbowej", col] = 0.0
        mat.at["Wynajem sprzętu (kopiarka , maty, maszyna do butów )", col] = 0.0
        mat.at["Inne usługi (szkolenie BHP)", col] = 0.0

        mat.at["Prowizje OTA&GDS", col] = 0.0
        mat.at["WYNIK DEPARTAMENTU", col] = sales_rooms  # na razie = sprzedaż (bez kosztów)
        mat.at["koszt na sprzedany pokój", col] = 0.0     # uzupełnisz po podpięciu kosztów

    # Sekcje rozdzielające – None, by wyświetlić puste pola
    for r in ROWS:
        if r.startswith("—"):
            mat.loc[r, :] = None
    return mat

# ======= Formatowanie =======
def _fmt(row: str, v):
    if pd.isna(v) or row.startswith("—"):
        return ""
    if row == "frekwencja":
        return f"{float(v)*100:,.1f}%".replace(",", " ")
    if row in {
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
    }:
        return f"{float(v):,.2f}".replace(",", " ").replace(".", ",")
    return f"{float(v):,.0f}".replace(",", " ")

# ======= UI =======
def render() -> None:
    year = int(st.session_state.get("year", 2025))
    init_exec_year(year)
    migrate_to_new_schema()

    st.header(f"Departament POKOJE — {year}")

    # Edytowalne „liczba pokoi” zapisywane per-rok w session_state
    rooms_store = st.session_state.setdefault("rooms_static_by_year", {})
    default_guess = None
    # Spróbuj oszacować z Operacji (maks. 'Pokoje do sprzedaży' z roku)
    exec_df = st.session_state.get("exec")
    if isinstance(exec_df, pd.DataFrame) and COL["available"] in exec_df.columns:
        try:
            df = exec_df.copy()
            df[COL["date"]] = pd.to_datetime(df[COL["date"]], errors="coerce")
            default_guess = int(_n(df.loc[df[COL["date"]].dt.year == year, COL["available"]]).max())
        except Exception:
            default_guess = None
    current_value = int(rooms_store.get(year, default_guess or 0))

    new_value = st.number_input("Liczba pokoi (edytowalne)", min_value=0, max_value=5000, step=1, value=current_value)
    if new_value != current_value:
        rooms_store[year] = int(new_value)
        st.session_state["rooms_static_by_year"] = rooms_store

    matrix = _build_matrix(year, rooms_static=float(rooms_store.get(year, new_value)))

    # Konwersja do tekstu dla prezentacji
    display = matrix.copy().astype(object)
    for r in display.index:
        for c in display.columns:
            display.at[r, c] = _fmt(r, display.at[r, c])

    st.dataframe(display, use_container_width=True)

# wymuś render w multipage
render()
