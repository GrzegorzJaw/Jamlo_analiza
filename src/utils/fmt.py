def fmt_pln(x):
    try:
        return f"{float(x):,.0f} PLN".replace(",", " ")
    except Exception:
        return str(x)
