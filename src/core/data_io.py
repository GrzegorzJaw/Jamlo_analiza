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
