import streamlit as st, pandas as pd
from core.state import init_session
from core.navigation import build_pages
from core.cloud_drive import download_excel_from_drive, upload_excel_to_drive
from core.data_io import read_project_excel
from core.i18n import PAGE_LABELS_PL, resolve_sheet_name

st.set_page_config(page_title="Analiza hotelowa", layout="wide")

# --- Logowanie / pliki ---
st.sidebar.title("Logowanie")
role = st.sidebar.radio("Rola", ["GM","INV"], index=0, horizontal=True)
proj_upload = st.sidebar.file_uploader("Projekt aplikacji (Excel)", type=["xlsx"])

# Projekt (zakładki/ACL) z uploadu albo fallbacku (ten, który dałeś)

project_sheets = read_project_excel(
    proj_upload,
    fallback_path="Projekt_aplikacji_hotelowej_20251028_074602.xlsx",
    alt_paths=["/mnt/data/Projekt_aplikacji_hotelowej_20251028_074602.xlsx"],
)
if not project_sheets:
    st.sidebar.warning("Nie znaleziono pliku projektu. Wgraj go w panelu lub upewnij się, że istnieje w /mnt/data/.")


st.sidebar.subheader("Google Drive — Plan Finansowy Hotele")
drive_file_id = st.secrets.get("DRIVE_FILE_ID_PLAN", "").strip()
if not drive_file_id:
    st.sidebar.error("Dodaj DRIVE_FILE_ID_PLAN w secrets.toml (ID pliku „Plan Finansowy Hotele.xlsm”).")

# Wczytanie danych z Drive + spięcie sesji
if st.sidebar.button("Zaloguj (wczytaj z chmury)", use_container_width=True):
    cloud_book = download_excel_from_drive(drive_file_id)
    init_session(st, data_book=cloud_book, project_sheets=project_sheets)
    st.session_state["data_book"] = cloud_book

# Jeżeli jeszcze nie zalogowano, zainicjuj pustą sesję
if "insights" not in st.session_state:
    init_session(st, data_book={}, project_sheets=project_sheets)

# Rozwiąż nazwy arkuszy (np. Rooms -> Pokoje) i zapisz w sesji
book = st.session_state.get("data_book", {})
st.session_state["sheets_map"] = {
    "PLAN": resolve_sheet_name(book, "PLAN") or "Plan",
    "WYKONANIE": resolve_sheet_name(book, "WYKONANIE") or "Wykonanie",
    "ROOMS": resolve_sheet_name(book, "ROOMS") or "Pokoje",
    "FNB": resolve_sheet_name(book, "FNB") or "Gastronomia",
    "OPEX": resolve_sheet_name(book, "OPEX") or "OPEX",
}

# Menu (Polskie etykiety w UI, wewnątrz zostają ID)
pages_ids = build_pages(role, project_sheets.get("Zakładki"), st.session_state["project_config"])
def _label(pid): return PAGE_LABELS_PL.get(pid, pid)
page = st.sidebar.radio("Nawigacja", pages_ids, format_func=_label)

readonly = (role == "INV")

# --- Router (nic nie zmieniaj poza polskimi nagłówkami w plikach stron) ---
from pages import dashboard_gm, plan, wykonanie, opex, rooms, fnb, raporty, covenants, tasks, settings
if page == "DASH_GM":       dashboard_gm.render(readonly=False)
elif page == "PLAN":        plan.render(readonly=readonly)
elif page == "WYKONANIE":   wykonanie.render(readonly=readonly)
elif page == "ROOMS":       rooms.render()
elif page == "FNB":         fnb.render()
elif page == "OPEX":        opex.render(readonly=readonly)
elif page == "RAPORTY":     raporty.render()
elif page == "COVENANTS":   covenants.render()
elif page == "TASKS":       tasks.render()
elif page == "SETTINGS":    settings.render(role, pages_ids)
else:                       st.info("Zakładka w przygotowaniu.")

# --- Zapisy do chmury (używamy rzeczywistych nazw arkuszy z sheets_map) ---
def _frames_for_save():
    sm = st.session_state.get("sheets_map", {})
    frames = {}
    plan_df = st.session_state.get("plan")
    if isinstance(plan_df, pd.DataFrame): frames[sm["PLAN"]] = plan_df
    actual_df = st.session_state.get("actual_daily")
    if isinstance(actual_df, pd.DataFrame): frames[sm["WYKONANIE"]] = actual_df
    return frames

col1, col2 = st.sidebar.columns(2)
if col1.button("Zapisz", use_container_width=True):
    frames = _frames_for_save()
    if frames: upload_excel_to_drive(drive_file_id, frames); st.sidebar.success("Zapisano na Google Drive.")
    else:      st.sidebar.warning("Brak danych do zapisu.")

if col2.button("Wyloguj", use_container_width=True):
    try:
        frames = _frames_for_save()
        if frames: upload_excel_to_drive(drive_file_id, frames)
    finally:
        st.session_state.clear()
        st.experimental_rerun()
