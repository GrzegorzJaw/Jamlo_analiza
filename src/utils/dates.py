import pandas as pd

def month_index(n=12):
    return pd.Index([f"{i:02d}" for i in range(1, n+1)], name="month")

def ensure_month(df: pd.DataFrame, n=12) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(index=month_index(n))
    df = df.copy()
    if "month" not in df.columns:
        df = df.reset_index().rename(columns={"index":"month"})
    df["month"] = df["month"].astype(str).str.zfill(2)
    df = df.set_index("month", drop=True)
    return df
