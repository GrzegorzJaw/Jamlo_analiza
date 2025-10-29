import numpy as np
from .data_io import coerce_num
from ..utils.dates import ensure_month

def enrich_insights(insights):
    ins = ensure_month(insights)
    ins = ins.copy()
    ins["RevPAR"] = coerce_num(ins.get("ADR")) * coerce_num(ins.get("occ"))
    fixed_unalloc = coerce_num(ins.get("fixed_costs", 0)).fillna(0) +                     coerce_num(ins.get("unalloc", 0)).fillna(0) +                     coerce_num(ins.get("mgmt_fees", 0)).fillna(0)
    denom = (coerce_num(ins.get("ADR", 0)) - coerce_num(ins.get("var_cost_per_occ_room", 0)))
    ins["BE_rooms"] = np.where(denom>0, fixed_unalloc/denom, np.nan)
    return ins
