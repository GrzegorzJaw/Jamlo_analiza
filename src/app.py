# app.py
from __future__ import annotations

import os
import pandas as pd
import streamlit as st

# Core
from core.state import init_session
from core.navigation import build_pages
from core.i18n import PAGE_LABELS_PL, resolve_sheet_name

# Tryb lokalny – bez Drive
USE_DRIVE = False  # docelowo ustawimy to na True, gdy wdrożymy eksport do GDrive

# Stuby, żeby reszta kodu się nie sypała, jeśli gdzieś jest wywołanie:
def resolve_drive_id(value: str) -> str: return ""
def download_excel_from_drive(file_id_or_url: str) -> dict: return {}
def upload_excel_to_drive(file_id_or_url: str, frames: dict) -> None: return None

# Strony
from pages import (
    dashboard_gm, plan, wykonanie, opex, rooms, fnb, raporty, covenants, tasks, settings
)

# --------------------------------------------------------------------
# USTAWIENIA STRONY
# --------------------------------------------------------------------
st.set_page_config(page_title="Analiza hotelowa", layout="wide")

# --------------------------------------------------------------------
# POMOCNICZE
# --------------------------------------------------------------------
def _xls_to_dict(path_or_file) -> dict[str, pd.DataFrame]:
    xls = pd.ExcelFile(path_or_file)
    return {name: xls.parse(name) for name in xls.sheet_names}

def _safe_render(mod, **kwargs):
    """Wywołaj stronę z argumentami, a jeśli ma starszą sygnaturę – bez nich."""
    try:
        return mod.render(**kwargs)
    except TypeError:
        return mod.render()

def _frames_for_save() -> dict[str, pd.DataFrame]:
    sm = st.session_state.get("sheets_map", {})
    out: dict[str, pd.DataFrame] = {}
    plan_df = st.session_state.get("plan")
    if isinstance(plan_df, pd.DataFrame) and sm.get("PLAN"):
        out[sm["PLAN"]] = plan_df
    actual_df = st.session_state.get("actual_daily")
    if isinstance(actual_df, pd.DataFrame) and sm.get("WYKONANIE"):
        out[sm["WYKONANIE"]] = actual_df
    return out

# --------------------------------------------------------------------
# SIDEBAR: LOGOWANIE + WYBÓR PROJEKTU
# --------------------------------------------------------------------
st.sidebar.title("Logowanie")
role = st.sidebar.radio("Rola", ["GM", "INV"], index=0, horizontal=True)

st.sidebar.subheader("Projekt aplikacji (Excel)")
proj_upload = st.sidebar.file_uploader("Wgraj plik projektu", type=["xlsx"])

# 1) z uploadu
project_sheets: dict[str, pd.DataFrame] = {}
if proj_upload is not None:
    try:
        project_sheets = _xls_to_dict(proj_upload)
    except Exception as e:
        st.sidebar.error(f"Nie mogę odczytać pliku projektu: {e}")

# 2) fallback – lokalnie w repo lub w /mnt/data
if not project_sheets:
    for p in [
        "Projekt_aplikacji_hotelowej_20251028_074602.xlsx",
        "/mnt/data/Projekt_aplikacji_hotelowej_20251028_074602.xlsx",
    ]:
        if os.path.exists(p):
            try:
                project_sheets = _xls_to_dict(p)
                break
            except Exception as e:
                st.sidebar.error(f"Problem z odczytem projektu ({p}): {e}")

if not project_sheets:
    st.sidebar.warning("Nie znaleziono pliku projektu. Wgraj go w panelu lub umieść w /mnt/data/.")

# --------------------------------------------------------------------
# GOOGLE DRIVE: ID + PRZYCISKI
# --------------------------------------------------------------------
st.sidebar.subheader("Google Drive — Plan Finansowy Hotele")
raw_drive_id = st.secrets.get("DRIVE_FILE_ID_PLAN", "")

try:
    drive_file_id = resolve_drive_id(raw_drive_id)
except Exception as e:
    drive_file_id = ""
    st.sidebar.error(f"ID pliku jest niepoprawne: {e}")

with st.sidebar.expander("Diagnostyka Drive", expanded=False):
    st.write("Sekret RAW:", repr(raw_drive_id))
    st.write("Wyłuskane ID:", repr(drive_file_id) if drive_file_id else "— brak —")

btn_login  = st.sidebar.button("Zaloguj (wczytaj z chmury)", use_container_width=True, disabled=not bool(drive_file_id))
btn_save   = st.sidebar.button("Zapisz do chmury", use_container_width=True, disabled=not bool(drive_file_id))
btn_logout = st.sidebar.button("Wyloguj (zapisz i wyczyść)", use_container_width=True)

# --------------------------------------------------------------------
# WĘZEŁ INICJALIZACJI SESJI
# --------------------------------------------------------------------
if btn_login and drive_file_id:
    try:
        cloud_book = download_excel_from_drive(drive_file_id)
        init_session(st, data_book=cloud_book, project_sheets=project_sheets)
        st.session_state["data_book"] = cloud_book
        st.sidebar.success("Dane z chmury wczytane.")
    except Exception as e:
        st.sidebar.error(f"Błąd pobierania z Google Drive: {e}")

# Jeżeli jeszcze nie zalogowano, zainicjuj pustą sesję (starter)
if "insights" not in st.session_state:
    init_session(st, data_book={}, project_sheets=project_sheets)

# Mapowanie nazw arkuszy -> ID zakładek (PL: Rooms -> Pokoje itd.)
book = st.session_state.get("data_book", {})
st.session_state["sheets_map"] = {
    "PLAN":       resolve_sheet_name(book, "PLAN")       or "Plan",
    "WYKONANIE":  resolve_sheet_name(book, "WYKONANIE")  or "Wykonanie",
    "ROOMS":      resolve_sheet_name(book, "ROOMS")      or "Pokoje",
    "FNB":        resolve_sheet_name(book, "FNB")        or "Gastronomia",
    "OPEX":       resolve_sheet_name(book, "OPEX")       or "OPEX",
}

# --------------------------------------------------------------------
# NAWIGACJA (etykiety po polsku)
# --------------------------------------------------------------------
pages_ids = build_pages(role, project_sheets.get("Zakładki"), st.session_state["project_config"])
page = st.sidebar.radio("Nawigacja", pages_ids, format_func=lambda pid: PAGE_LABELS_PL.get(pid, pid))
readonly = (role == "INV")

# --------------------------------------------------------------------
# ROUTER STRON
# --------------------------------------------------------------------
if page == "DASH_GM":
    _safe_render(dashboard_gm, readonly=False)
elif page == "PLAN":
    _safe_render(plan, readonly=readonly)
elif page == "WYKONANIE":
    _safe_render(wykonanie, readonly=readonly)
elif page == "ROOMS":
    _safe_render(rooms)
elif page == "FNB":
    _safe_render(fnb)
elif page == "OPEX":
    _safe_render(opex, readonly=readonly)
elif page == "RAPORTY":
    _safe_render(raporty)
elif page == "COVENANTS":
    _safe_render(covenants)
elif page == "TASKS":
    _safe_render(tasks)
elif page == "SETTINGS":
    _safe_render(settings, role=role, pages_ids=pages_ids)
else:
    st.info("Zakładka w przygotowaniu.")

# --------------------------------------------------------------------
# ZAPIS / WYLOGOWANIE
# --------------------------------------------------------------------
if btn_save and drive_file_id:
    frames = _frames_for_save()
    if not frames:
        st.sidebar.warning("Brak danych do zapisu (Plan/Wykonanie).")
    else:
        try:
            upload_excel_to_drive(drive_file_id, frames)
            st.sidebar.success("Zapisano na Google Drive.")
        except Exception as e:
            st.sidebar.error(f"Nie udało się zapisać: {e}")

if btn_logout:
    # jeśli mamy ID – spróbuj zapisać
    try:
        if drive_file_id:
            frames = _frames_for_save()
            if frames:
                upload_excel_to_drive(drive_file_id, frames)
    finally:
        st.session_state.clear()
        st.experimental_rerun()
