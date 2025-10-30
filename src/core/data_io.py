import os
from pathlib import Path
import pandas as pd
from typing import Dict, Iterable

def _xls_to_dict(xls: pd.ExcelFile) -> Dict[str, pd.DataFrame]:
    return {name: xls.parse(name) for name in xls.sheet_names}

def read_project_excel(
    uploaded_file=None,
    fallback_path: str | None = None,
    alt_paths: Iterable[str] | None = None,
) -> Dict[str, pd.DataFrame]:
    """
    1) Jeśli użytkownik wgrał plik – czyta z uploadu.
    2) W innym wypadku próbuje znaleźć plik projektu po ścieżkach fallback.
    3) Gdy nic nie znaleziono – zwraca pusty dict.
    """
    # 1) z uploadu
    if uploaded_file is not None:
        xls = pd.ExcelFile(uploaded_file)
        return _xls_to_dict(xls)

    # 2) fallbacki
    candidates = []
    if fallback_path:
        candidates.append(fallback_path)

    # domyślne ścieżki (repo + katalog danych na serwerze)
    default_name = "Projekt_aplikacji_hotelowej_20251028_074602.xlsx"
    here = Path(__file__).resolve().parents[1]  # katalog src/
    candidates += [
        str(here / default_name),
        str(Path("/mnt/data") / default_name),
    ]

    if alt_paths:
        candidates += list(alt_paths)

    for p in candidates:
        if p and os.path.exists(p):
            xls = pd.ExcelFile(p)
            return _xls_to_dict(xls)

    # 3) brak pliku – pusto
    return {}

# --- core/data_io.py (DOPISZ NA KOŃCU PLIKU) ---

def coerce_num(s):
    """Bezpieczne rzutowanie kolumn na liczby (używane m.in. w plan.py)."""
    return pd.to_numeric(s, errors="coerce").fillna(0.0)

def default_frames():
    """
    Zwraca trzy ramki: insights (miesięczna baza), raw (dzienna baza), kpi (pusta tabela KPI).
    To jest tylko „starter”, aby appka poprawnie wstała bez wgranych danych.
    """
    # Oś czasu: bieżący rok, miesiące 1..12
    year_start = pd.Timestamp.today().normalize().replace(month=1, day=1)
    months = pd.period_range(start=year_start, periods=12, freq="M").to_timestamp()

    # INSIGHTS – to na bazie tego budujesz 'plan' w state.py
    insights = pd.DataFrame({
        "month": months,                          # utils.dates.ensure_month zadziała
        "ADR": 300.0,                             # średnia cena
        "occ": 0.65,                              # obłożenie (0..1)
        "var_cost_per_occ_room": 45.0,            # zmienny koszt na sprz. pokój
        "fixed_costs": 120000.0/12,               # stałe koszty miesięczne
        "unalloc": 0.0,                           # koszty niealokowane (opcjonalnie)
        "mgmt_fees": 0.0,                         # opłaty zarządcze (opcjonalnie)
    })

    # RAW – dzienne (puste kolumny, żeby nic się nie wywalało)
    raw = pd.DataFrame({
        "date": pd.date_range(months[0], months[-1], freq="D"),
        "sold_rooms": pd.Series(dtype="float"),
        "ADR": pd.Series(dtype="float"),
        "fnb_rev": pd.Series(dtype="float"),
        "other_rev": pd.Series(dtype="float"),
    })

    # KPI – prosty szkielet, jeśli gdzieś podglądasz kpi.head()
    kpi = pd.DataFrame({
        "metric": [],
        "value": []
    })

    return insights, raw, kpi
