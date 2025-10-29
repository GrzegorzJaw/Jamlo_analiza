import pandas as pd
import unicodedata
from typing import Dict, List


def _canon(s: str) -> str:
    if s is None:
        return ""
    # lower + strip diacritics + remove punctuation/spaces
    s = str(s).strip().lower()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    for ch in [" ", "\t", "\n", "\r", "_", "-", "/", "\\", "(", ")", ":", ";", ",", ".", "[", "]"]:
        s = s.replace(ch, "")
    return s


def _pick_col(df: pd.DataFrame, variants: List[str]) -> str | None:
    """Zwraca NAZWĘ ISTNIEJĄCEJ kolumny (oryginalną) dopasowanej do wariantów po kanonizacji."""
    if df is None or df.empty:
        return None
    canon_map = {_canon(c): c for c in df.columns}
    for v in variants:
        key = _canon(v)
        if key in canon_map:
            return canon_map[key]
    return None


class ProjectConfig:
    """Czyta arkusze projektu i normalizuje do ram: tabs, interactions, proc, acl."""
    def __init__(self, sheets: Dict[str, pd.DataFrame] | None):
        self.sheets = sheets or {}

        self.tabs = self._norm_tabs(self.sheets.get("Zakładki") or self.sheets.get("Zakladki"))
        self.interactions = self._norm_interactions(self.sheets.get("Interakcje"))
        self.proc = self._norm_proc(self.sheets.get("Plan_roczny_procesy"))
        self.acl = self._norm_acl(self.sheets.get("Uprawnienia"))

    # --------- Normalizacje arkuszy ---------
    def _norm_tabs(self, df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame(columns=["id", "persona", "desc", "inputs", "outputs"])

        idc = _pick_col(df, ["zakladka (id)", "zakładka (id)", "id", "tab id", "zakladka"])
        persona = _pick_col(df, ["persona (gm/inv)", "persona", "rola", "role"])
        desc = _pick_col(df, ["cel biznesowy (1 zdanie)", "cel", "opis", "description"])
        inputs = _pick_col(df, ["wejścia danych (źródła)", "wejscia danych (zrodla)", "wejscia", "inputs", "zrodla", "źródła"])
        outputs = _pick_col(df, ["wyjścia / interakcje", "wyjscia / interakcje", "wyjscia", "outputs", "interakcje", "actions"])

        out = pd.DataFrame()
        out["id"] = df[idc] if idc else pd.Series(["DASH_GM"] * len(df))
        out["persona"] = (df[persona] if persona else pd.Series(["GM,INV"] * len(df))).astype(str).str.upper()
        out["desc"] = (df[desc] if desc else "").astype(str)
        out["inputs"] = (df[inputs] if inputs else "").astype(str)
        out["outputs"] = (df[outputs] if outputs else "").astype(str)
        return out

    def _norm_interactions(self, df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame(columns=["src", "event", "dst", "effect", "type"])

        src = _pick_col(df, ["z źródło (zakładka)", "zrodlo (zakladka)", "zrodlo", "source", "src", "from", "z"])
        ev = _pick_col(df, ["akcja / zdarzenie", "akcja", "event", "action"])
        dst = _pick_col(df, ["do cel (zakładka)", "cel (zakladka)", "target", "dst", "to", "do"])
        eff = _pick_col(df, ["skutek (krótki opis)", "skutek", "opis skutku", "effect", "result"])
        typ = _pick_col(df, ["typ interakcji (nawigacja / obliczenia / walidacja / eksport)", "typ interakcji", "typ", "type"])

        out = pd.DataFrame()
        out["src"] = (df[src] if src else "").astype(str)
        out["event"] = (df[ev] if ev else "").astype(str)
        out["dst"] = (df[dst] if dst else "").astype(str)
        out["effect"] = (df[eff] if eff else "").astype(str)
        out["type"] = (df[typ] if typ else "").astype(str)
        return out

    def _norm_proc(self, df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame(columns=["area", "step", "owner", "input", "output", "freq", "note"])

        area = _pick_col(df, ["obszar (rooms/f&b/opex/…)", "obszar", "area"])
        step = _pick_col(df, ["krok procesu", "krok", "step"])
        owner = _pick_col(df, ["właściciel", "wlasciciel", "owner"])
        _in = _pick_col(df, ["wejście (dane/plik)", "wejscie (dane/plik)", "wejscie", "input"])
        _out = _pick_col(df, ["wyjście (artefakt)", "wyjscie (artefakt)", "wyjscie", "output"])
        freq = _pick_col(df, ["częstotliwość", "czestotliwosc", "freq", "frequency"])
        note = _pick_col(df, ["uwagi", "uwaga", "note", "notes"])

        out = pd.DataFrame()
        out["area"] = (df[area] if area else "").astype(str)
        out["step"] = (df[step] if step else "").astype(str)
        out["owner"] = (df[owner] if owner else "").astype(str)
        out["input"] = (df[_in] if _in else "").astype(str)
        out["output"] = (df[_out] if _out else "").astype(str)
        out["freq"] = (df[freq] if freq else "").astype(str)
        out["note"] = (df[note] if note else "").astype(str)
        return out

    def _norm_acl(self, df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame(columns=["id", "GM", "INV"])
        idc = _pick_col(df, ["zakladka (id)", "zakładka (id)", "id", "zakladka"])
        gm = _pick_col(df, ["gm (read/write)", "gm"])
        inv = _pick_col(df, ["inv (read/write)", "inv"])
        out = pd.DataFrame()
        out["id"] = (df[idc] if idc else "").astype(str)
        out["GM"] = (df[gm] if gm else "write")
        out["INV"] = (df[inv] if inv else "read")
        return out

    # --------- Uprawnienia i nawigacja ---------
    def role_can_write(self, page_id: str, role: str) -> bool:
        role = (role or "").upper()
        if role == "GM":
            # GM ma write, chyba że ACL mówi inaczej
            default = True
        else:
            default = False
        if self.acl is None or self.acl.empty:
            return default
        row = self.acl.loc[self.acl["id"].astype(str) == str(page_id)]
        if row.empty:
            return default
        val = str(row.iloc[0][role]).strip().lower()
        return val in {"w", "write", "rw", "r/w", "read/write", "edit", "edytuj"}

    def pages_for_role(self, role: str) -> list:
        if self.tabs is None or self.tabs.empty:
            return ["DASH_GM", "PLAN", "WYKONANIE", "RAPORTY"] if (role or "").upper() == "GM" else ["DASH_INV", "RAPORTY"]
        r = (role or "").upper()
        allowed = self.tabs.loc[self.tabs["persona"].str.contains(r, case=False, regex=True), "id"].astype(str).tolist()
        # ARCH pokaż jeśli są interakcje/procesy
        if (self.interactions is not None and not self.interactions.empty) or (self.proc is not None and not self.proc.empty):
            if "ARCH" not in allowed:
                allowed.append("ARCH")
        return allowed or (["DASH_GM"] if r == "GM" else ["DASH_INV"])

    # --------- Graf przepływów ---------
    def lineage_edges(self) -> pd.DataFrame:
        edges = []
        if self.tabs is not None and not self.tabs.empty:
            for _, r in self.tabs.iterrows():
                src = str(r.get("id", "")).strip()
                ins = str(r.get("inputs", "")).strip()
                outs = str(r.get("outputs", "")).strip()
                inputs = [x.strip() for x in ins.replace(",", ";").split(";") if x.strip()]
                outputs = [x.strip() for x in outs.replace(",", ";").split(";") if x.strip()]
                for i in inputs:
                    edges.append((i, src, "input"))
                for o in outputs:
                    edges.append((src, o, "output"))
        df = pd.DataFrame(edges, columns=["src", "dst", "kind"]).drop_duplicates()

        if self.interactions is not None and not self.interactions.empty:
            inter = self.interactions.copy()
            inter["kind"] = "event"
            inter = inter.rename(columns={"event": "note"})
            inter = inter[["src", "dst", "kind", "note"]]
            # dopasuj kolumny
            if "note" not in df.columns:
                df["note"] = ""
            df = pd.concat([df, inter], ignore_index=True, sort=False).fillna("")
        return df
