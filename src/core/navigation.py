def build_pages(role: str, project_tabs_df, project_config=None):
    if project_config is not None:
        return project_config.pages_for_role(role)

    # Fallback (gdy brak configu)
    canonical = [
        "DASH_GM","DASH_INV","PLAN","WYKONANIE","ROOMS","FNB",
        "OPEX","RAPORTY","COVENANTS","TASKS","SETTINGS"
    ]
    if project_tabs_df is None or project_tabs_df.empty:
        return ["DASH_GM","PLAN","WYKONANIE","RAPORTY"] if role=="GM" else ["DASH_INV","RAPORTY"]
    df = project_tabs_df.copy()
    cols = {c.lower(): c for c in df.columns}
    idc = cols.get("zakładka (id)") or cols.get("zakladka (id)") or list(df.columns)[0]
    persona = cols.get("persona (gm/inv)") or cols.get("persona") or list(df.columns)[1]
    df["id"] = df[idc].astype(str)
    df["persona"] = df[persona].astype(str).str.upper()
    allowed = df.loc[df["persona"].str.contains(role, case=False, regex=True), "id"].tolist()
    return [p for p in canonical if p in allowed] or (["DASH_GM"] if role=="GM" else ["DASH_INV"])
