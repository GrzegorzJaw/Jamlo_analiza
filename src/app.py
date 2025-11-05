# app.py
import importlib
from typing import Optional

import streamlit as st


# --- Ustawienia strony ---
st.set_page_config(
    page_title="Finansowy Hotele — Analiza",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --- Helpers: bezpieczne importy i render ---
def _try_import(path: str):
    try:
        return importlib.import_module(path)
    except Exception:
        return None


def _safe_render(page_mod, *, title: Optional[str] = None):
    """Wywołuje page_mod.render() jeśli istnieje, inaczej pokazuje komunikat."""
    if title:
        st.header(title)
    if page_mod is None:
        st.info("Moduł strony nie został odnaleziony.")
        return
    render = getattr(page_mod, "render", None)
    if callable(render):
        try:
            render()
        except Exception as ex:
            st.error(f"Błąd podczas renderowania strony: {ex}")
    else:
        st.info("Ta strona nie ma funkcji render().")


# --- Import stron (jeśli istnieją) ---
page_rooms = _try_import("pages.rooms")
page_wykonanie = _try_import("pages.wykonanie")  # nieużywane tutaj, ale bywa przydatne


# --- Tytuł aplikacji / header ---
st.sidebar.markdown("## **FINANSOWY HOTELE**")

# UWAGA:
# Zgodnie z wymaganiem NIE ruszamy sekcji poniżej tytułu.
# Jeśli masz tam własne widgety (rola/rok/miesiąc itd.), pozostaw je jak były
# — ten plik nic tam nie dodaje ani nie usuwa.

# --- Nowa nawigacja w SIDEBAR: Departamenty + pod-zakładki dla Kosztów ---
DEPARTMENTS = [
    "Pokoje",
    "Gastronomia",
    "Administracja i Dyrekcja",
    "Dział Sprzedaży",
    "Dział Techniczny",
    "Koszty",
    "Pozostałe Centra",
]

st.sidebar.markdown("---")
st.sidebar.markdown("### Departamenty")

st.session_state["dept"] = st.sidebar.radio(
    "Wybierz departament",
    options=DEPARTMENTS,
    index=DEPARTMENTS.index(st.session_state.get("dept", "Pokoje")),
    key="dept_radio",
)

if st.session_state["dept"] == "Koszty":
    st.session_state["dept_cost_tab"] = st.sidebar.radio(
        "→ Koszty (podzakładki)",
        options=["Koszty bieżące", "Koszty ogólne"],
        index=0 if st.session_state.get("dept_cost_tab") not in ["Koszty bieżące", "Koszty ogólne"] else
        ["Koszty bieżące", "Koszty ogólne"].index(st.session_state["dept_cost_tab"]),
        key="dept_cost_radio",
    )

# --- Główna treść: routing wg wyboru departamentu ---
dept = st.session_state.get("dept", "Pokoje")

if dept == "Pokoje":
    # Render strony z macierzą 12×N wyliczaną z dziennika „Wykonanie”
    _safe_render(page_rooms, title="Pokoje — podsumowania miesięczne")

elif dept == "Gastronomia":
    st.header("Gastronomia — podsumowania miesięczne")
    st.info("Placeholder. Podłączę źródła po doprecyzowaniu mapowania pól z dziennika/planów.")

elif dept == "Administracja i Dyrekcja":
    st.header("Administracja i Dyrekcja — podsumowania miesięczne")
    st.info("Placeholder. Analogiczny widok do Pokoje.")

elif dept == "Dział Sprzedaży":
    st.header("Dział Sprzedaży — podsumowania miesięczne")
    st.info("Placeholder. Analogiczny widok do Pokoje.")

elif dept == "Dział Techniczny":
    st.header("Dział Techniczny — podsumowania miesięczne")
    st.info("Placeholder. Analogiczny widok do Pokoje.")

elif dept == "Koszty":
    sub = st.session_state.get("dept_cost_tab", "Koszty bieżące")
    st.header(f"Koszty — {sub}")
    st.info("Placeholder dla dwóch widoków kosztowych (bieżące/ogólne).")

elif dept == "Pozostałe Centra":
    st.header("Pozostałe Centra — podsumowania miesięczne")
    st.info("Placeholder. Analogiczny widok do Pokoje.")


# --- Footer / diagnostyka (opcjonalnie) ---
with st.expander("Diag: stan sesji (dev)"):
    st.write({k: v for k, v in st.session_state.items() if k in ["dept", "dept_cost_tab"]})
