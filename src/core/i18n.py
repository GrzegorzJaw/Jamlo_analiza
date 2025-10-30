# Polskie etykiety zakładek (UI)
PAGE_LABELS_PL = {
    "DASH_GM": "Pulpit GM",
    "DASH_INV": "Pulpit Inwestora",
    "PLAN": "Plan",
    "WYKONANIE": "Wykonanie",
    "ROOMS": "Pokoje",
    "FNB": "Gastronomia",
    "OPEX": "Koszty operacyjne",
    "RAPORTY": "Raporty",
    "COVENANTS": "Kowenanty",
    "TASKS": "Zadania",
    "SETTINGS": "Ustawienia",
}

# Kandydaci nazw arkuszy w pliku .xlsm dla danej zakładki
SHEET_CANDIDATES = {
    "PLAN": ["Plan", "BUDŻET", "Budget"],
    "WYKONANIE": ["Wykonanie", "Actual", "Rzeczywiste"],
    "ROOMS": ["Pokoje", "Rooms"],
    "FNB": ["Gastronomia", "F&B", "FNB"],
    "OPEX": ["OPEX", "Koszty operacyjne", "Koszty_OPEX"],
}
def resolve_sheet_name(book: dict, page_id: str) -> str | None:
    names = set(book.keys())
    for cand in SHEET_CANDIDATES.get(page_id, []):
        if cand in names:
            return cand
    return None
