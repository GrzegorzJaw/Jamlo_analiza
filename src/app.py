# app.py
from __future__ import annotations

import os
from typing import Any, Callable, Optional

import streamlit as st

# ==== Tryb pracy: lokalny (bez wczytywania/pliku w chmurze na starcie) ====
LOCAL_ONLY = True  # gdy przejdziemy do pracy z GDrive, ustawimy False/wykryjemy z env

# ==== Importy stron (bez wymuszania obecności wszystkich modułów) ====
def _try_import(path: str) -> Optional[Any]:
    try:
        module = __import__(path, fromlist=["render"])
        return module
    except Exception:
        return None

dashboard_gm = _try_import("pages.dashboard_gm")
plan = _try_import("pages.plan")
wykonanie = _try_import("pages.wykonanie")
raporty = _try_import("pages.raporty")

# ==== Prosty init sesji (bez I/O) ====
def _ensure_defaults() -> None:
    s = st.session_state
    s.setdefault("nav", "Wykonanie")
    s.setdefault("role", "GM")   # GM = analityk, INV = inwestor
    s.setdefault("year", 2025)
    s.setdefault("month", 1)
    # miejsce na inne Twoje klucze, nie kasujemy istniejących:
    s.setdefault("insights", {})     # zgodność z Twoim wcześniejszym init_session
    s.setdefault("data_book", {})    # projekt/plan, obecnie nieużywany w LOCAL_ONLY
    s.setdefault("project_sheets", {})

MONTHS_PL = ["sty", "lut", "mar", "kwi", "maj", "cze", "lip", "sie", "wrz", "paź", "lis", "gru"]


# ==== Pomocnicze: bezpieczne wywołanie render() z różnymi sygnaturami ====
def _safe_render(mod: Any, **kwargs) -> None:
    """Dlaczego: strony mogą mieć różne sygnatury render()."""
    if mod is None:
        st.info("Moduł strony jest obecnie niedostępny.")
        return
    render: Callable[..., Any] = getattr(mod, "render", None)
    if render is None:
        st.info("Strona nie udostępnia funkcji render().")
        return
    try:
        render(**kwargs)
    except TypeError:
        # stara sygnatura bez parametrów
        render()


# ==== Sidebar: NAWIGACJA na górze, niżej kontekst (rola/rok/miesiąc) ====
def _sidebar_context_and_nav() -> tuple[str, bool, int, int]:
    _ensure_defaults()

    st.sidebar.title("Finansowy Hotele")

    # --- ewentualna sekcja chmury (wyłączona w LOCAL_ONLY) ---
    with st.sidebar.expander("Diagnostyka Drive", expanded=False):
        st.caption("Tryb lokalny – wczytywanie/zapis do chmury wyłączone.")
        st.button("Zaloguj (wczytaj z chmury)", disabled=True)
        st.button("Zapisz do chmury", disabled=True)
        st.button("Wyloguj (zapisz i wyczyść)", disabled=True)

    # --- NAWIGACJA (TOP) ---
    nav = st.sidebar.radio(
        "Nawigacja",
        options=["Pulpit GM", "Plan", "Wykonanie", "Raporty"],
        index=["Pulpit GM", "Plan", "Wykonanie", "Raporty"].index(st.session_state["nav"]),
        horizontal=False,
    )
    st.session_state["nav"] = nav

    st.sidebar.markdown("---")

    # --- KONTEKST (BELOW) ---
    role_label = st.sidebar.selectbox(
        "Rola",
        options=["GM (analityk)", "INV (inwestor)"],
        index=0 if st.session_state["role"] == "GM" else 1,
    )
    st.session_state["role"] = "INV" if role_label.startswith("INV") else "GM"
    is_inv = st.session_state["role"] == "INV"

    year = int(
        st.sidebar.number_input(
            "Rok", min_value=2000, max_value=2100, value=int(st.session_state["year"]), step=1
        )
    )
    st.session_state["year"] = year

    month = int(
        st.sidebar.selectbox(
            "Miesiąc",
            options=list(range(1, 13)),
            index=(int(st.session_state["month"]) - 1),
            format_func=lambda m: f"{MONTHS_PL[m-1]} ({m:02d})",
        )
    )
    st.session_state["month"] = month

    st.sidebar.caption("Dane żyją w sesji. Eksport do XLSX wykonasz w zakładce Wykonanie.")

    return nav, is_inv, year, month


# ==== Pasek nagłówka z kontekstem + skróty miesiąc -/+ ====
def _header(nav: str, is_inv: bool, year: int, month: int) -> None:
    col1, col2, col3 = st.columns([6, 1, 1])
    with col1:
        st.markdown(
            f"### {nav}  ·  Rola: **{'INV' if is_inv else 'GM'}**  ·  "
            f"Rok: **{year}**  ·  Miesiąc: **{MONTHS_PL[month-1]} ({month:02d})**"
        )
    with col2:
        if st.button("◀︎", help="Poprzedni miesiąc"):
            new_m = month - 1
            new_y = year
            if new_m < 1:
                new_m = 12
                new_y -= 1
            st.session_state["month"] = new_m
            st.session_state["year"] = new_y
            st.rerun()
    with col3:
        if st.button("▶︎", help="Następny miesiąc"):
            new_m = month + 1
            new_y = year
            if new_m > 12:
                new_m = 1
                new_y += 1
            st.session_state["month"] = new_m
            st.session_state["year"] = new_y
            st.rerun()


# ==== Router stron ====
def _route(nav: str, is_inv: bool, year: int, month: int) -> None:
    if nav == "Pulpit GM":
        _safe_render(dashboard_gm, year=year, month=month, readonly=is_inv)
    elif nav == "Plan":
        _safe_render(plan, year=year, month=month, readonly=is_inv)
    elif nav == "Wykonanie":
        # Strona Wykonanie działa lokalnie na session_state i pozwala eksport do XLSX.
        try:
            _safe_render(wykonanie, readonly=is_inv)
        except TypeError:
            _safe_render(wykonanie)
    elif nav == "Raporty":
        _safe_render(raporty, year=year, month=month, readonly=is_inv)
    else:
        st.info("Zakładka w przygotowaniu.")


# ==== Wejście aplikacji ====
def main() -> None:
    st.set_page_config(page_title="Analiza hotelowa – tryb lokalny", layout="wide")

    # Inicjalizacja domyślnego stanu (bez żadnego wczytywania zewnętrznego)
    _ensure_defaults()

    # Sidebar (Nawigacja na górze, niżej Rola/Rok/Miesiąc)
    nav, is_inv, year, month = _sidebar_context_and_nav()

    # Nagłówek z kontekstem + skróty zmiany miesiąca
    _header(nav, is_inv, year, month)

    # Render wybranej strony
    _route(nav, is_inv, year, month)


if __name__ == "__main__":
    main()
