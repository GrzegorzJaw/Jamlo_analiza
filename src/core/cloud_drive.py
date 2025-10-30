import io, json, tempfile, pandas as pd, streamlit as st
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

def _drive():
    if "_gdrive" in st.session_state: return st.session_state["_gdrive"]
    sa_dict = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT_JSON"])
    gauth = GoogleAuth(settings={"client_config_backend":"service","service_config":{"client_json":sa_dict}})
    gauth.ServiceAuth()
    drv = GoogleDrive(gauth); st.session_state["_gdrive"]=drv; return drv

def download_excel_from_drive(file_id: str) -> dict[str, pd.DataFrame]:
    drv = _drive(); f = drv.CreateFile({'id': file_id})
    with tempfile.NamedTemporaryFile(suffix=".xlsm", delete=False) as tmp:
        f.GetContentFile(tmp.name)  # .xlsm OK z openpyxl
        xls = pd.ExcelFile(tmp.name, engine="openpyxl")
    return {name: xls.parse(name) for name in xls.sheet_names}

def upload_excel_to_drive(file_id: str, frames: dict[str, pd.DataFrame]):
    with tempfile.NamedTemporaryFile(suffix=".xlsm", delete=False) as tmp:
        with pd.ExcelWriter(tmp.name, engine="openpyxl") as wr:
            for sheet, df in frames.items():
                if isinstance(df, pd.DataFrame):
                    df.to_excel(wr, index=False, sheet_name=sheet[:31] or "Sheet1")
        path = tmp.name
    drv = _drive(); f = drv.CreateFile({'id': file_id}); f.SetContentFile(path); f.Upload()
