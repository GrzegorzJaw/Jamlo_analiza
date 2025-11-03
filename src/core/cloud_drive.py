# =========================================
# state.py  (ZMIANY: zapis/odczyt do TEGO SAMEGO pliku na Drive)
# =========================================
import os
from datetime import date
from typing import Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st

from cloud_drive import upsert_sheet, read_sheet  # <— NOWE
# (reszta importów Twojej logiki plan/kpi – bez zmian)

# --- kolumny dzienne (jak ustaliliśmy wcześniej) ---
ROOMS_DAY_COLS = ["pokoje_do_sprzedania","pokoje_oos","sprzedane_pokoje_bez","sprzedane_pokoje_ze","przychody_pokoje_netto"]
FNB_REVENUE_DAY_COLS = ["fnb_sniadania_pakietowe","fnb_kolacje_pakietowe","fnb_zywnosc_a_la_carte","fnb_napoje_a_la_carte","fnb_zywnosc_bankiety","fnb_napoje_bankiety","fnb_wynajem_sali","fnb_catering"]
OTHER_REVENUE_DAY_COLS = ["proc_pokoi_parking","przychody_parking","przychody_sklep_recepcyjny","przychody_pralnia_gosci","przychody_transport_gosci","przychody_rekreacja","przychody_pozostale"]
ROOMS_COST_PERSONNEL = ["r_osobowe_wynagrodzenia","r_osobowe_zus","r_osobowe_pfron","r_osobowe_wyzywienie","r_osobowe_odziez_bhp","r_osobowe_medyczne","r_osobowe_inne"]
ROOMS_COST_MATERIALS = ["r_materialy_eksploatacyjne_spozywcze","r_materialy_kosmetyki_srodki","r_materialy_inne_biurowe"]
ROOMS_COST_SERVICES = ["r_uslugi_sprzatania","r_uslugi_pranie_zew","r_uslugi_pranie_odziezy_sluzbowej","r_uslugi_wynajem_sprzetu","r_uslugi_inne_bhp"]
ROOMS_COST_OTHER = ["r_pozostale_prowizje_ota_gds"]
FNB_COST_RAW = ["g_koszt_surowca_zywnosc_pln","g_koszt_surowca_napoje_pln"]
FNB_COST_PERSONNEL = ["g_osobowe_wynagrodzenia","g_osobowe_zus","g_osobowe_pfron","g_osobowe_wyzywienie","g_osobowe_odziez_bhp","g_osobowe_medyczne","g_osobowe_inne"]
FNB_COST_MATERIALS = ["g_materialy_zastawa","g_materialy_drobne_wyposazenie","g_materialy_bielizna_dekoracje","g_materialy_karty_dan","g_materialy_srodki_czystosci","g_materialy_inne"]
FNB_COST_SERVICES = ["g_uslugi_sprzatania_tapicerki","g_uslugi_pranie_odziezy_sluzbowej","g_uslugi_pranie_bielizny_gastro","g_uslugi_wynajem_sprzetu_lokali","g_uslugi_inne"]
DAY_COLUMNS: List[str] = (
    ROOMS_DAY_COLS + FNB_REVENUE_DAY_COLS + OTHER_REVENUE_DAY_COLS +
    ROOMS_COST_PERSONNEL + ROOMS_COST_MATERIALS + ROOMS_COST_SERVICES + ROOMS_COST_OTHER +
    FNB_COST_RAW + FNB_COST_PERSONNEL + FNB_COST_MATERIALS + FNB_COST_SERVICES
)

# --- nazewnictwo arkuszy w Excelu ---
def _sheet_name(year: int, month: int) -> str:
    return f"WYKONANIE_{year}_{month:02d}"  # <= zgodnie z ustaleniami

def _month_dates(year: int, month: int) -> List[pd.Timestamp]:
    start = pd.Timestamp(year=year, month=month, day=1)
    end = (start + pd.offsets.MonthBegin(1))
    return list(pd.date_range(start, end - pd.Timedelta(days=1), freq="D"))

def _create_month_df(year: int, month: int) -> pd.DataFrame:
    df = pd.DataFrame({"data": _month_dates(year, month)})
    for c in DAY_COLUMNS:
        df[c] = 0.0
    return df

# --- stan w sesji Streamlit ---
def _ensure_exec(year: int) -> None:
    if "exec" not in st.session_state:
        st.session_state["exec"] = {}
    if year not in st.session_state["exec"]:
        st.session_state["exec"][year] = {}
    if "exec_audit" not in st.session_state:
        st.session_state["exec_audit"] = {}
    if year not in st.session_state["exec_audit"]:
        st.session_state["exec_audit"][year] = {}
    if "drive_plan_file" not in st.session_state:
        # priorytet: secrets → UI może nadpisać
        st.session_state["drive_plan_file"] = (
            st.secrets.get("PLAN_FILE_ID") or st.secrets.get("PLAN_FILE_URL") or ""
        )

def init_exec_year(year: int, drive_id_or_url: Optional[str] = None) -> None:
    """Tworzy/ładuje 12 miesięcy. Jeśli w pliku na Drive istnieją arkusze WYKONANIE_YYYY_MM – wczytuje je."""
    _ensure_exec(year)
    if drive_id_or_url:
        st.session_state["drive_plan_file"] = drive_id_or_url
    file_ref = st.session_state["drive_plan_file"]

    for m in range(1, 13):
        # próbuj wczytać arkusz z Drive
        df_cloud = None
        if file_ref:
            try:
                df_cloud = read_sheet(file_ref, _sheet_name(year, m))
            except Exception:
                df_cloud = None
        if df_cloud is not None and isinstance(df_cloud, pd.DataFrame) and "data" in df_cloud.columns:
            # sanity: upewnij się, że data jest datą
            df_cloud = df_cloud.copy()
            df_cloud["data"] = pd.to_datetime(df_cloud["data"])
            for c in DAY_COLUMNS:
                if c not in df_cloud.columns:
                    df_cloud[c] = 0.0
            st.session_state["exec"][year][m] = df_cloud
        else:
            st.session_state["exec"][year][m] = _create_month_df(year, m)
        st.session_state["exec_audit"][year][m] = []

def get_month_df(year: int, month: int) -> pd.DataFrame:
    _ensure_exec(year)
    return st.session_state["exec"][year][month].copy(deep=True)

def _diff_frames(before: pd.DataFrame, after: pd.DataFrame) -> pd.DataFrame:
    before = before.sort_values("data").reset_index(drop=True)
    after = after.sort_values("data").reset_index(drop=True)
    rows = []
    for col in after.columns:
        if col == "data":
            continue
        dif = before[col] != after[col]
        if dif.any():
            changed = after.loc[dif, ["data", col]].copy()
            changed["kolumna"] = col
            changed["stara_wartosc"] = before.loc[dif, col].values
            changed["nowa_wartosc"] = after.loc[dif, col].values
            rows.append(changed[["data", "kolumna", "stara_wartosc", "nowa_wartosc"]])
    if rows:
        out = pd.concat(rows, ignore_index=True)
        out["data"] = pd.to_datetime(out["data"]).dt.date
        return out
    return pd.DataFrame(columns=["data", "kolumna", "stara_wartosc", "nowa_wartosc"])

def _save_month_to_drive(year: int, month: int, df: pd.DataFrame) -> None:
    """Podmień/utwórz arkusz WYKONANIE_YYYY_MM w TYM SAMYM pliku na Drive."""
    file_ref = st.session_state.get("drive_plan_file", "")
    if not file_ref:
        # bezpiecznie: jeśli nie znamy pliku – nie wysyłamy (tylko sesja)
        return
    # zachowujemy wszystkie inne arkusze – upsert działa na kopii workbooka
    upsert_sheet(file_ref, _sheet_name(year, month), df)

def save_month_df(year: int, month: int, edited: pd.DataFrame, user: str = "GM") -> pd.DataFrame:
    """Zapis: audit + upload do tego samego pliku na Drive (+ stan w sesji)."""
    _ensure_exec(year)
    before = st.session_state["exec"][year][month]
    changes = _diff_frames(before, edited)

    if not changes.empty:
        audit = st.session_state["exec_audit"][year][month]
        ts = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
        for _, r in changes.iterrows():
            audit.append({
                "czas": ts, "kto": user,
                "data": r["data"].isoformat() if hasattr(r["data"], "isoformat") else str(r["data"]),
                "kolumna": r["kolumna"],
                "stara": float(r["stara_wartosc"]),
                "nowa": float(r["nowa_wartosc"]),
            })
        st.session_state["exec_audit"][year][month] = audit

    # zaktualizuj w sesji
    st.session_state["exec"][year][month] = edited.copy(deep=True)

    # wyślij w to samo miejsce w Drive (jeden arkusz)
    try:
        _save_month_to_drive(year, month, edited)
    except Exception as e:
        st.warning(f"Nie udało się zapisać do Google Drive: {e}")

    return changes

def get_audit(year: int, month: int) -> pd.DataFrame:
    _ensure_exec(year)
    return pd.DataFrame(st.session_state["exec_audit"][year][month])

def split_editable(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    today = pd.Timestamp.today().normalize()
    d = df.copy()
    d["data"] = pd.to_datetime(d["data"])
    return d[d["data"] <= today].copy(), d[d["data"] > today].copy()

def missing_days(df: pd.DataFrame) -> pd.Series:
    return df.loc[df["przychody_pokoje_netto"] <= 0.0, "data"]
