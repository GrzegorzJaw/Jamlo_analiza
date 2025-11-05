# core/i18n.py

# Polskie etykiety zakładek (UI)
PAGE_LABELS_PL = {
    "DASH_GM":  "Pulpit GM",
    "DASH_INV": "Pulpit Inwestora",
    "PLAN":     "Plan",
    "WYKONANIE":"Wykonanie",

    # Departamenty
    "ROOMS":    "Pokoje",
    "FNB":      "Gastronomia",
    "ADMIN":    "Administracja i Dyrekcja",
    "SALES":    "Dział Sprzedaży",
    "TECH":     "Dział Techniczny",
    "OPEX":     "Koszty",
    "OTHER":    "Pozostałe Centra",

    # Pozostałe
    "RAPORTY":  "Raporty",
    "COVENANTS":"Kowenanty",
    "TASKS":    "Zadania",
    "SETTINGS": "Ustawienia",
}

# Kandydaci nazw arkuszy w pliku .xlsm dla danej zakładki
SHEET_CANDIDATES = {
    "PLAN":       ["Plan", "BUDŻET", "Budget"],
    "WYKONANIE":  ["Wykonanie", "Actual", "Rzeczywiste"],

    # Departamenty
    "ROOMS":      ["Pokoje", "Rooms"],
    "FNB":        ["Gastronomia", "F&B", "FNB"],
    "ADMIN":      ["Administracja i Dyrekcja", "Administracja", "Dyrekcja", "Admin"],
    "SALES":      ["Dział Sprzedaży", "Sprzedaż", "Sales"],
    "TECH":       ["Dział Techniczny", "Techniczny", "Technika", "Maintenance"],
    "OPEX":       ["OPEX", "Koszty operacyjne", "Koszty_OPEX", "Koszty"],
    "OTHER":      ["Pozostałe Centra", "Pozostałe", "Inne Centra", "Other"],
}

def resolve_sheet_name(book: dict, page_id: str) -> str | None:
    names = set(book.keys())
    for cand in SHEET_CANDIDATES.get(page_id, []):
        if cand in names:
            return cand
    return None
