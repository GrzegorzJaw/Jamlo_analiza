import numpy as np
import pandas as pd
from core.data_io import coerce_num

def monthly_var_vs_plan(insights_baseline: pd.DataFrame, actual_daily: pd.DataFrame) -> pd.DataFrame:
    """
    Zwraca tabelę m/m: Plan(ADR, Occ, RevPAR_plan), Actual(ADR_avg, sold), VAR (RevPAR).
    actual_daily oczekuje kolumn: date, sold_rooms, ADR (średnia dzienna – proxy przy sumowaniu).
    """
    if insights_baseline is None or insights_baseline.empty:
        return pd.DataFrame()

    base = insights_baseline.copy()
    if "month" not in base.index.names:
        base = base.reset_index()
    else:
        base = base.reset_index()
    base = base[["month", "ADR", "occ"]].copy()
    base["ADR"] = coerce_num(base["ADR"])
    base["occ"] = coerce_num(base["occ"])
    base["RevPAR_plan"] = base["ADR"] * base["occ"]

    if actual_daily is None or actual_daily.empty:
        base["sold"] = np.nan
        base["ADR_avg"] = np.nan
        base["RevPAR_act"] = np.nan
        base["VAR_RevPAR"] = np.nan
        return base

    df = actual_daily.copy()
    df["month"] = pd.to_datetime(df["date"]).dt.month.map(lambda x: f"{int(x):02d}")
    agg = df.groupby("month", as_index=False).agg(
        sold=("sold_rooms", "sum"),
        rooms_rev=("ADR", lambda s: np.nansum(s.values)),
    )
    agg["ADR_avg"] = agg["rooms_rev"] / agg["sold"].replace(0, np.nan)

    out = base.merge(agg, on="month", how="left")
    out["RevPAR_act"] = out["ADR_avg"] * out["occ"]
    out["VAR_RevPAR"] = out["RevPAR_act"] - out["RevPAR_plan"]
    return out
