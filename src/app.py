import streamlit as st
from core.data_io import read_project_excel, read_data_workbook
from core.navigation import build_pages
from core.state import init_session
from core.config import ProjectConfig
from pages import dashboard_gm, dashboard_inv, plan, wykonanie, rooms, fnb, opex, raporty, covenants, tasks, settings

try:
    from pages import arch
    HAS_ARCH = True
except Exception:
    HAS_ARCH = False

st.set_page_config(page_title="JAMLO Hotel Analytics", layout="wide")

# Sidebar
st.sidebar.title("Logowanie / Konfiguracja")
role = st.sidebar.selectbox("Rola", ["GM", "INV"], index=0, help="GM: edycja; INV: tylko odczyt")
project_xlsx = st.sidebar.file_uploader("Projekt aplikacji (Excel)", type=["xlsx"])
data_xlsx = st.sidebar.file_uploader("Dane operacyjne (Excel)", type=["xlsx"])

# Load sheets & data
project_sheets = read_project_excel(project_xlsx)
project_cfg = ProjectConfig(project_sheets)

data_book = read_data_workbook(data_xlsx)
init_session(st, data_book, project_sheets=project_sheets)

# Navigation & ACL
pages_ids = build_pages(role, project_sheets.get("Zakładki"), project_config=project_cfg)
page = st.sidebar.radio("Nawigacja", pages_ids)

readonly = not project_cfg.role_can_write(page, role)

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
elif page == "ARCH" and HAS_ARCH:
    arch.render(project_cfg)
else:
    st.info("Ta zakładka nie jest jeszcze zaimplementowana.")
