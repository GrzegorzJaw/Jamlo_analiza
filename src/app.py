# app.py
from __future__ import annotations

from typing import Any, Callable, Optional

import streamlit as st

# ========= Tryb pracy =========
LOCAL_ONLY = True  # zostawiamy lokalny; Drive dołączymy później

# ========= Helper do bezpiecznych importów stron =========
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

MONTHS_PL = ["sty", "lut", "mar", "kwi", "maj", "cze", "lip", "sie", "wrz", "paź", "lis", "gru"]


# ========= Session defaults =========
def _ensure_defaults() -> None:
    s = st.session_state
    s.setdefault("nav", "Wykonanie")
    s.setdefault("role", "GM")   # GM = analityk, INV = inwestor
    s.setdefault("year", 2025)
    s.setdefault("month", 1)
    s.setdefault("insights", {})
    s.setdefault("data_book", {})
    s.setdefault("project_sheets", {})


# ========= Safe render (różne sygnatury) =========
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
        render()


# ========= Sidebar: NAWIGACJA (top) + kontekst (below) =========
def _sidebar_context_and_nav() -> tuple[str, bool, int, int]:
    _ensure_defaults()

    st.sidebar.title("Finansowy Hotele")

    with st.sidebar.expander("Diagnostyka Drive", expanded=False):
        st.caption("Tryb lokalny – integracje z chmurą wyłączone.")
        st.button("Zaloguj (wczytaj z chmury)", disabled=True, key="drv_login")
        st.button("Zapisz do chmury", disabled=True, key="drv_save")
        st.button("Wyloguj (zapisz i wyczyść)", disabled=True, key="drv_logout")

    # --- NAWIGACJA (TOP) ---
    nav = st.sidebar.radio(
        "Nawigacja",
        options=["Pulpit GM", "Plan", "Wykonanie", "Raporty"],
        index=["Pulpit GM", "Plan", "Wykonanie", "Raporty"].index(st.session_state["nav"]),
        key="nav_radio",  # <<< unikalny key
    )
    st.session_state["nav"] = nav

    st.sidebar.markdown("---")

    # --- KONTEKST (BELOW) ---
    role_label = st.sidebar.selectbox(
        "Rola",
        options=["GM (analityk)", "INV (inwestor)"],
        index=0 if st.session_state["role"] == "GM" else 1,
        key="role_select",  # <<< unikalny key
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
            key="year_input",  # <<< unikalny key
        )
    )
    st.session_state["year"] = year

    month = int(
        st.sidebar.selectbox(
            "Miesiąc",
            options=list(range(1, 13)),
            index=(int(st.session_state["month"]) - 1),
            format_func=lambda m: f"{MONTHS_PL[m-1]} ({m:02d})",
            key="month_select",  # <<< unikalny key
        )
    )
    st.session_state["month"] = month

    st.sidebar.caption("Dane żyją w sesji. Eksport do XLSX wykonasz w zakładce Wykonanie.")

    return nav, is_inv, year, month


# ========= Header z kontekstem + skróty miesiąc -/+ =========
def _header(nav: str, is_inv: bool, year: int, month: int) -> None:
    c1, c2, c3 = st.columns([6, 1, 1])
    with c1:
        st.markdown(
            f"### {nav}  ·  Rola: **{'INV' if is_inv else 'GM'}**  ·  "
            f"Rok: **{year}**  ·  Miesiąc: **{MONTHS_PL[month-1]} ({month:02d})**"
        )
    with c2:
        if st.button("◀︎", help="Poprzedni miesiąc", key="month_prev"):
            new_m, new_y = (month - 1, year)
            if new_m < 1:
                new_m, new_y = 12, year - 1
            st.session_state["month"] = new_m
            st.session_state["year"] = new_y
            st.rerun()
    with c3:
        if st.button("▶︎", help="Następny miesiąc", key="month_next"):
            new_m, new_y = (month + 1, year)
            if new_m > 12:
                new_m, new_y = 1, year + 1
            st.session_state["month"] = new_m
            st.session_state["year"] = new_y
            st.rerun()


# ========= Router =========
def _route(nav: str, is_inv: bool, year: int, month: int) -> None:
    if nav == "Pulpit GM":
        _safe_render(dashboard_gm, year=year, month=month, readonly=is_inv)
    elif nav == "Plan":
        _safe_render(plan, year=year, month=month, readonly=is_inv)
    elif nav == "Wykonanie":
        # Strona Wykonanie pracuje lokalnie na session_state i nie rysuje sidebaru
        try:
            _safe_render(wykonanie, readonly=is_inv)
        except TypeError:
            _safe_render(wykonanie)
    elif nav == "Raporty":
        _safe_render(raporty, year=year, month=month, readonly=is_inv)
    else:
        st.info("Zakładka w przygotowaniu.")


# ========= Entry =========
def main() -> None:
    st.set_page_config(page_title="Analiza hotelowa – tryb lokalny", layout="wide")
    _ensure_defaults()
    nav, is_inv, year, month = _sidebar_context_and_nav()
    _header(nav, is_inv, year, month)
    _route(nav, is_inv, year, month)


if __name__ == "__main__":
    main()
