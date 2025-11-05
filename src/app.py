# ===============================
# file: app.py
# ===============================
from __future__ import annotations

from typing import Any, Callable, Optional

import streamlit as st

# --- Strony ładowane leniwie (bez twardych zależności) ---
def _try_import(path: str) -> Optional[Any]:
    try:
        return __import__(path, fromlist=["render"])
    except Exception:
        return None


dashboard_gm = _try_import("pages.dashboard_gm")
plan = _try_import("pages.plan")
wykonanie = _try_import("pages.wykonanie")
raporty = _try_import("pages.raporty")

# --- Stan lokalny: inicjalizacja roku i migracja schematu kolumn ---
from core.state_local import init_exec_year, migrate_to_new_schema

MONTHS_PL = ["sty", "lut", "mar", "kwi", "maj", "cze", "lip", "sie", "wrz", "paź", "lis", "gru"]


# ---------------------------------------------------------------------
# Session defaults
# ---------------------------------------------------------------------
def _ensure_defaults() -> None:
    s = st.session_state
    s.setdefault("nav", "Wykonanie")
    s.setdefault("role", "GM")  # GM = analityk, INV = inwestor
    s.setdefault("year", 2025)
    s.setdefault("month", 1)


# ---------------------------------------------------------------------
# Safe render (różne sygnatury)
# ---------------------------------------------------------------------
def _safe_render(mod: Any, **kwargs) -> None:
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
        # kompatybilność wsteczna (stare strony bez parametrów)
        render()


# ---------------------------------------------------------------------
# Sidebar: NAWIGACJA (top) + KONTEKST (below)
# ---------------------------------------------------------------------
def _sidebar_context_and_nav() -> tuple[str, bool, int, int]:
    """
    Jeden zestaw kontrolek globalnych.
    Dlaczego: unikamy duplikatów elementów (StreamlitDuplicateElementId).
    """
    _ensure_defaults()

    st.sidebar.title("Finansowy Hotele")

    # Nawigacja NA GÓRZE
    nav = st.sidebar.radio(
        "Nawigacja",
        options=["Pulpit GM", "Plan", "Wykonanie", "Raporty"],
        index=["Pulpit GM", "Plan", "Wykonanie", "Raporty"].index(st.session_state["nav"]),
        key="nav_radio",
    )
    st.session_state["nav"] = nav

    st.sidebar.markdown("---")

    # KONTEKST (rola/rok/miesiąc)
    role_label = st.sidebar.selectbox(
        "Rola",
        options=["GM (analityk)", "INV (inwestor)"],
        index=0 if st.session_state["role"] == "GM" else 1,
        key="role_select",
    )
    st.session_state["role"] = "INV" if role_label.startswith("INV") else "GM"
    is_inv = st.session_state["role"] == "INV"

    year = int(
        st.sidebar.number_input(
            "Rok",
            min_value=2000,
            max_value=2100,
            value=int(st.session_state["year"]),
            step=1,
            key="year_input",
        )
    )
    st.session_state["year"] = year

    month = int(
        st.sidebar.selectbox(
            "Miesiąc",
            options=list(range(1, 13)),
            index=(int(st.session_state["month"]) - 1),
            format_func=lambda m: f"{MONTHS_PL[m-1]} ({m:02d})",
            key="month_select",
        )
    )
    st.session_state["month"] = month

    st.sidebar.caption("Dane żyją lokalnie w sesji. Eksport do XLSX wykonasz w zakładce „Wykonanie”.")
    return nav, is_inv, year, month


# ---------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------
def _route(nav: str, is_inv: bool, year: int, month: int) -> None:
    """
    Centralny przełącznik stron.
    Ważne: każdorazowo dbamy o spójność danych (init + migracja).
    """
    # Utrzymanie spójności schematu (nowe nazwy kolumn) i gotowych miesięcy
    init_exec_year(year)
    migrate_to_new_schema()

    if nav == "Pulpit GM":
        _safe_render(dashboard_gm, year=year, month=month, readonly=is_inv)
    elif nav == "Plan":
        _safe_render(plan, year=year, month=month, readonly=is_inv)
    elif nav == "Wykonanie":
        # strona sama rysuje nagłówek i strzałki miesięcy
        try:
            _safe_render(wykonanie, readonly=is_inv)
        except TypeError:
            _safe_render(wykonanie)
    elif nav == "Raporty":
        _safe_render(raporty, year=year, month=month, readonly=is_inv)
    else:
        st.info("Zakładka w przygotowaniu.")


# ---------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------
def main() -> None:
    st.set_page_config(page_title="Analiza hotelowa", layout="wide")
    _ensure_defaults()
    nav, is_inv, year, month = _sidebar_context_and_nav()
    # Nie rysujemy tu nagłówków – każdy moduł sam odpowiada za swój tytuł
    _route(nav, is_inv, year, month)


if __name__ == "__main__":
    main()
