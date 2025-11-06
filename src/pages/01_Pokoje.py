# src/pages/01_Pokoje.py
from __future__ import annotations
import pandas as pd
import streamlit as st

# ──────────────────────────────────────────────────────────────────────────────
# Próba importu get_month_df; jeśli brak – zwróć pusty DataFrame (fallback)
# ──────────────────────────────────────────────────────────────────────────────
try:
    from core.state_local import get_month_df  # noqa: F401
except Exception:
    def get_month_df(year: int, month: int) -> pd.DataFrame:  # type: ignore
        return pd.DataFrame()

MONTHS = ["sty","lut","mar","kwi","maj","cze","lip","sie","wrz","paź","lis","gru"]

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
    "ZUS","PFRON","Wyżywienie","Odzież służbowa i bhp","Usługi medyczne","Inne",

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

# Mapowanie nazw kolumn w dzienniku „Operacje” (dopasuj, jeśli masz inne nagłówki)
COL = {
    "date": "Data",
    "available": "Pokoje do sprzedaży",
    "oos": "Pokoje OOS",
    "sold_bez": "Sprzedane BEZ śn.",
    "sold_ze": "Sprzedane ZE śn.",
    "revenue_rooms": "Przychody pokoje (netto)",     # do wyliczenia RevPOR
    "sales_sm": "Sprzedaż pokoi S&M (netto)",        # opcjonalnie
}

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────
def _n(x) -> pd.Series:
    """Zwróć Series[float] nawet dla scala/None/list."""
    if isinstance(x, pd.Series):
        return pd.to_numeric(x, errors="coerce").fillna(0.0)
    try:
        s = pd.Series(x)
    except Exception:
        s = pd.Series([0.0])
    return pd.to_numeric(s, errors="coerce").fillna(0.0)

def _detect_date_col(df: pd.DataFrame) -> str | None:
    for c in ("Data", "data", "Date", "date"):
        if c in df.columns:
            return c
    # heurystyka awaryjna
    best, best_ok = None, -1
    for c in df.columns:
        try:
            ok = pd.to_datetime(df[c], errors="coerce").notna().sum()
            if ok > best_ok:
                best, best_ok = c, ok
        except Exception:
            pass
    return best

def _month_from_exec(year: int, month: int) -> pd.DataFrame:
    """Fallback: weź dziennik 'Operacje' z session_state i wyfiltruj YYYY-MM."""
    exec_df = st.session_state.get("exec")
    if not isinstance(exec_df, pd.DataFrame) or exec_df.empty:
        return pd.DataFrame()
    dcol = _detect_date_col(exec_df)
    if not dcol:
        return pd.DataFrame()
    df = exec_df.copy()
    df[dcol] = pd.to_datetime(df[dcol], errors="coerce")
    return df[(df[dcol].dt.year == year) & (df[dcol].dt.month == month)]

# ──────────────────────────────────────────────────────────────────────────────
# KPI jednego miesiąca (zgodnie z „Podsumowania KPI”)
# ──────────────────────────────────────────────────────────────────────────────
def _kpi_month(df: pd.DataFrame) -> dict[str, float]:
    if df is None or df.empty:
        return dict(available=0.0, sold=0.0, occ=0.0, revpor=0.0, sm=0.0)
    av  = _n(df.get(COL["available"])).sum()
    oos = _n(df.get(COL["oos"])).sum()
    capacity = max(float(av - oos), 0.0)
    sold = (_n(df.get(COL["sold_bez"])) + _n(df.get(COL["sold_ze"]))).sum()
    revenue_rooms = _n(df.get(COL["revenue_rooms"])).sum()
    revpor = float(revenue_rooms / sold) if sold > 0 else 0.0
    occ = float(sold / capacity) if capacity > 0 else 0.0
    sm = _n(df.get(COL["sales_sm"])).sum() if COL.get("sales_sm") in df.columns else 0.0
    return dict(available=capacity, sold=float(sold), occ=occ, revpor=revpor, sm=float(sm))

# ──────────────────────────────────────────────────────────────────────────────
# Budowa macierzy 12×N (get_month_df → fallback na dziennik z Operacji)
# ──────────────────────────────────────────────────────────────────────────────
def _build_rooms_matrix(year: int, rooms_static: float) -> pd.DataFrame:
    months: dict[int, dict[str, float]] = {}
    for m in range(1, 13):
        df_m = get_month_df(year, m)
        if df_m is None or getattr(df_m, "empty", True):
            df_m = _month_from_exec(year, m)
        months[m] = _kpi_month(df_m)

    mat = pd.DataFrame(0.0, index=ROWS, columns=MONTHS, dtype=float)
    for m in range(1, 13):
        col = MONTHS[m-1]
        k = months[m]
        capacity = k["available"]
        sold     = k["sold"]
        occ      = k["occ"]
        revpor   = k["revpor"]
        sm       = k["sm"]
        sales_rooms = sold * revpor  # Twoja reguła

        mat.at["liczba pokoi", col]                 = rooms_static
        mat.at["zdolność eksploatacyjna", col]      = capacity
        mat.at["sprzedane pokojonoce", col]         = sold
        mat.at["frekwencja", col]                   = occ
        mat.at["średnia cena (RevPOR)", col]        = revpor

        mat.at["Sprzedaż pokoi", col]               = sales_rooms
        mat.at["Sprzedaż pokoi S&M", col]           = sm
        mat.at["Koszty wydziałowe", col]            = 0.0  # placeholders do podpięcia

        for r in [
            "Wynagrodzenie brutto i umowy zlecenia","ZUS","PFRON","Wyżywienie",
            "Odzież służbowa i bhp","Usługi medyczne","Inne",
            "Materiały eksploatacyjne, Artykuły spożywcze",
            "Kosmetyki dla gości (płyn, mydło), Środki czystości 1,5",
            "Inne materiały, w tym karty meldunkowe, galanteria papiernicza, art. biurowe",
            "Usługi sprzątania","Usługi prania (z wyłączeniem odzieży służbowej)",
            "Usługi prania odzieży służbowej","Wynajem sprzętu (kopiarka , maty, maszyna do butów )",
            "Inne usługi (szkolenie BHP)","Prowizje OTA&GDS",
        ]:
            mat.at[r, col] = 0.0

        mat.at["WYNIK DEPARTAMENTU", col]           = sales_rooms  # do czasu kosztów
        mat.at["koszt na sprzedany pokój", col]     = 0.0

    for r in ROWS:
        if r.startswith("—"):
            mat.loc[r, :] = None
    return mat

# ──────────────────────────────────────────────────────────────────────────────
# Formatowanie do prezentacji
# ──────────────────────────────────────────────────────────────────────────────
def _fmt(row: str, v):
    if pd.isna(v) or row.startswith("—"):
        return ""
    if row == "frekwencja":
        return f"{float(v)*100:,.1f}%".replace(",", " ")
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
    if row in money_rows:
        return f"{float(v):,.2f}".replace(",", " ").replace(".", ",")
    return f"{float(v):,.0f}".replace(",", " ")

# ──────────────────────────────────────────────────────────────────────────────
# UI
# ──────────────────────────────────────────────────────────────────────────────
def render() -> None:
    # Czekaj na dziennik z Operacji; bez tego nie liczymy KPI
    exec_df = st.session_state.get("exec")
    if not isinstance(exec_df, pd.DataFrame) or exec_df.empty:
        st.info("Brak danych w sesji. Wejdź najpierw do zakładki Operacje i zapisz miesiąc.")
        return

    # Rok: z sesji lub heurystyka z dziennika
    if "year" in st.session_state and st.session_state["year"]:
        year = int(st.session_state["year"])
    else:
        dcol = _detect_date_col(exec_df)
        if not dcol:
            st.warning("Nie wykryto kolumny daty w dzienniku Operacje.")
            return
        year = int(pd.to_datetime(exec_df[dcol], errors="coerce").dt.year.mode().iloc[0])

    st.header(f"Departament POKOJE — {year}")

    # Edytowalna „liczba pokoi” (przechowywana per-rok)
    rooms_store = st.session_state.setdefault("rooms_static_by_year", {})
    # podpowiedź: max 'Pokoje do sprzedaży' w danym roku
    try:
        dcol = _detect_date_col(exec_df)
        df_tmp = exec_df.copy()
        df_tmp[dcol] = pd.to_datetime(df_tmp[dcol], errors="coerce")
        default_guess = int(_n(df_tmp.loc[df_tmp[dcol].dt.year == year, COL["available"]]).max())
    except Exception:
        default_guess = 0
    current_value = int(rooms_store.get(year, default_guess))
    new_value = st.number_input("Liczba pokoi (edytowalne)", min_value=0, max_value=5000, step=1, value=current_value)
    if new_value != current_value:
        rooms_store[year] = int(new_value)
        st.session_state["rooms_static_by_year"] = rooms_store

    matrix = _build_rooms_matrix(year, rooms_static=float(rooms_store.get(year, new_value)))

    display = matrix.copy().astype(object)
    for r in display.index:
        for c in display.columns:
            display.at[r, c] = _fmt(r, display.at[r, c])
    st.dataframe(display, use_container_width=True)

# W multipage Streamlit plik strony jest wykonywany po wejściu w zakładkę,
# nie wywołujemy render() na siłę, aby nie kolidować z „Operacjami”.
# Jeśli chcesz wymusić, odkomentuj poniższe dwie linie, ale zwykle NIE jest to potrzebne:
# if __name__ == "__main__":
#     render()
