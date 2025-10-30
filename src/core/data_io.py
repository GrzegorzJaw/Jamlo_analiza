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
    Starter bez danych: miesięczne 'insights', dzienne 'raw' (wszystkie kolumny tej samej długości),
    oraz pusta tabela 'kpi'.
    """
    # kalendarz roku bieżącego
    today = pd.Timestamp.today().normalize()
    year_start = pd.Timestamp(today.year, 1, 1)
    year_end   = pd.Timestamp(today.year, 12, 31)

    # INSIGHTS (miesięczne)
    months = pd.period_range(start=year_start, end=year_end, freq="M").to_timestamp("M")
    insights = pd.DataFrame({
        "month": months,
        "ADR": 300.0,
        "occ": 0.65,
        "var_cost_per_occ_room": 45.0,
        "fixed_costs": 120000.0/12,
        "unalloc": 0.0,
        "mgmt_fees": 0.0,
    })

    # RAW (dzienne) — puste wartości, ale długości jak 'date'
    dates = pd.date_range(year_start, year_end, freq="D")
    n = len(dates)
    raw = pd.DataFrame({
        "date": dates,
        "sold_rooms": pd.Series([pd.NA] * n, dtype="Float64"),
        "ADR":        pd.Series([pd.NA] * n, dtype="Float64"),
        "fnb_rev":    pd.Series([pd.NA] * n, dtype="Float64"),
        "other_rev":  pd.Series([pd.NA] * n, dtype="Float64"),
    })

    # KPI – szkielet
    kpi = pd.DataFrame({"metric": [], "value": []})

    return insights, raw, kpi

