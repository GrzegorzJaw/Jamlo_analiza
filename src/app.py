import streamlit as st
import pandas as pd
from core.data_io import read_project_excel, read_data_workbook
from core.navigation import build_pages
from core.state import init_session
from pages import dashboard_gm, dashboard_inv, plan, wykonanie, rooms, fnb, opex, raporty, covenants, tasks, settings

st.set_page_config(page_title="JAMLO Hotel Analytics", layout="wide")

# Sidebar: role + uploads
st.sidebar.title("Logowanie / Konfiguracja")
role = st.sidebar.selectbox("Rola", ["GM", "INV"], index=0, help="GM: edycja; INV: tylko odczyt")
project_xlsx = st.sidebar.file_uploader("Projekt aplikacji (Excel)", type=["xlsx"])
data_xlsx = st.sidebar.file_uploader("Dane operacyjne (Excel)", type=["xlsx"])

# Load Excel project & data
project = read_project_excel(project_xlsx)
project_tabs = project.get("Zakładki")
data_book = read_data_workbook(data_xlsx)

# Init session data
init_session(st, data_book)

# Build navigation
pages_ids = build_pages(role, project_tabs)
page = st.sidebar.radio("Nawigacja", pages_ids)

# Readonly switch
readonly = (role == "INV")

# Router
if page == "DASH_GM":
    dashboard_gm.render()
elif page == "DASH_INV":
    dashboard_inv.render()
elif page == "PLAN":
    plan.render(readonly)
elif page == "WYKONANIE":
    wykonanie.render(readonly)
elif page == "ROOMS":
    rooms.render()
elif page == "FNB":
    fnb.render()
elif page == "OPEX":
    opex.render(readonly)
elif page == "RAPORTY":
    raporty.render()
elif page == "COVENANTS":
    covenants.render()
elif page == "TASKS":
    tasks.render()
elif page == "SETTINGS":
    settings.render(role, pages_ids)
else:
    st.info("Ta zakładka nie jest jeszcze zaimplementowana.")
