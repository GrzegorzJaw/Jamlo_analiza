# core/cloud_drive.py
from __future__ import annotations

import os
import re
import json
import base64
import tempfile
from typing import Dict

import pandas as pd
import streamlit as st


# ---------- Helpers: credentials & file-id ----------

def _load_sa_dict() -> Dict:
    """
    Ładuje poświadczenia konta usługi z `st.secrets["GOOGLE_SERVICE_ACCOUNT_JSON"]`.
    Akceptuje:
      - dict (sekcja TOML)
      - czysty JSON (string w potrójnych cudzysłowach)
      - base64(JSON)
      - ścieżkę do lokalnego pliku JSON
    Dodatkowo wycina sam fragment { ... } jeśli w stringu pojawiły się komentarze/śmieci.
    """
    val = st.secrets.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if isinstance(val, dict):
        return val
    if not val:
        raise RuntimeError("Brak GOOGLE_SERVICE_ACCOUNT_JSON w secrets.")

    s = str(val).strip()

    # spróbuj wyciąć czysty blok JSON { ... }
    m = re.search(r"\{.*\}", s, flags=re.S)
    if m:
        s_candidate = m.group(0)
        try:
            return json.loads(s_candidate)
        except Exception:
            pass  # spróbujemy kolejne ścieżki

    # czysty JSON bez wycinania
    try:
        return json.loads(s)
    except Exception:
        pass

    # base64(JSON)
    try:
        decoded = base64.b64decode(s)
        return json.loads(decoded.decode("utf-8"))
    except Exception:
        pass

    # ścieżka do pliku JSON
    if os.path.exists(s):
        with open(s, "r", encoding="utf-8") as f:
            return json.load(f)

    raise RuntimeError(
        "Nie mogę zdekodować GOOGLE_SERVICE_ACCOUNT_JSON. "
        "Upewnij się, że w secrets.toml jest pełny JSON (w potrójnych cudzysłowach), "
        "albo sekcja TOML z kluczami, albo base64(JSON), albo ścieżka do pliku."
    )


def resolve_drive_id(value: str) -> str:
    """
    Przyjmuje ID pliku albo pełny URL i zwraca samo ID pliku.
    Odrzuca `gid` (to ID arkusza, nie pliku).
    """
    v = (value or "").strip()
    if not v:
        return ""

    # URL typu /d/<ID>/
    m = re.search(r"/d/([a-zA-Z0-9_-]{20,})", v)
    if m:
        return m.group(1)

    # URL z parametrem ?id=<ID>
    m = re.search(r"[?&]id=([a-zA-Z0-9_-]{20,})", v)
    if m:
        return m.group(1)

    # jeśli to `gid` arkusza – zgłoś błąd
    if "gid=" in v or v.isdigit():
        raise ValueError(
            "Podano gid arkusza lub numer – potrzebne jest ID pliku Google Drive. "
            "Skopiuj fragment między /d/ a /view z adresu pliku."
        )

    # wygląda jak samo ID
    return v


# ---------- Google Drive client (lazy import) ----------

def _drive():
    """
    Zwraca zautoryzowany obiekt GoogleDrive (pydrive2). Importuje leniwie pydrive2 i cache'uje klienta w session_state.
    """
    try:
        from pydrive2.auth import GoogleAuth
        from pydrive2.drive import GoogleDrive
    except ModuleNotFoundError:
        st.error("Brakuje pakietu 'pydrive2'. Dodaj do requirements.txt: pydrive2, google-auth, google-api-python-client.")
        raise

    if "_gdrive" in st.session_state:
        return st.session_state["_gdrive"]

    sa_dict = _load_sa_dict()
    gauth = GoogleAuth(settings={
        "client_config_backend": "service",
        "service_config": {"client_json": sa_dict}
    })
    gauth.ServiceAuth()
    drv = GoogleDrive(gauth)
    st.session_state["_gdrive"] = drv
    return drv


# ---------- IO: download / upload Excel ----------

def _read_excel_to_dict(path: str) -> Dict[str, pd.DataFrame]:
    """
    Czyta .xlsx/.xlsm do dict[nazwa_arkusza] = DataFrame.
    """
    # openpyxl obsługuje też .xlsm (bez VBA interpretacji)
    xls = pd.ExcelFile(path, engine="openpyxl")
    return {name: xls.parse(name) for name in xls.sheet_names}


def download_excel_from_drive(file_id_or_url: str) -> Dict[str, pd.DataFrame]:
    """
    Pobiera plik Excel (.xlsx/.xlsm) z Google Drive i zwraca dict arkuszy.
    """
    file_id = resolve_drive_id(file_id_or_url)
    if not file_id:
        raise ValueError("Brak ID pliku Google Drive.")

    drv = _drive()
    f = drv.CreateFile({'id': file_id})

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        # Zachowujemy rozszerzenie .xlsm? Nie jest to konieczne dla odczytu,
        # ale jeśli chcesz, wykryj typ MIME (pomijamy dla prostoty).
        f.GetContentFile(tmp.name)
        return _read_excel_to_dict(tmp.name)


def upload_excel_to_drive(file_id_or_url: str, frames: Dict[str, pd.DataFrame]) -> None:
    """
    Zapisuje podane arkusze do pliku na Google Drive, nadpisując jego zawartość.
    UWAGA: zapis przez openpyxl nadpisuje treść i usunie ewentualne makra (VBA) z .xlsm.
    Traktuj więc ten plik jako „magazyn danych”, nie jako nośnik makr.
    """
    if not frames:
        return

    file_id = resolve_drive_id(file_id_or_url)
    if not file_id:
        raise ValueError("Brak ID pliku Google Drive.")

    # zapisz lokalnie tymczasowy plik
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        path = tmp.name
    with pd.ExcelWriter(path, engine="openpyxl") as wr:
        for sheet, df in frames.items():
            if isinstance(df, pd.DataFrame):
                # nazwa arkusza max 31 znaków (Excel)
                wr_sheet = (sheet or "Sheet1")[:31]
                df.to_excel(wr, index=False, sheet_name=wr_sheet)

    # wgraj na Drive
    drv = _drive()
    f = drv.CreateFile({'id': file_id})
    f.SetContentFile(path)
    f.Upload()
