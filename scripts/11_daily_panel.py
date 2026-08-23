#!/usr/bin/env python3
"""Step 11: aggregate the option-level VRP panel to a daily (date, root, tenor)
panel. Only rv_status == 'ok' rows enter. Within each (date, economic_root,
target_tenor) cell the up-to-6 selected ATM contracts (calls and puts, top 3
by the step-6 rerank) are equal-weight averaged.

Output: clean_v3/vrp_v3/daily_panel_step11/daily_vrp_panel_v3.parquet
"""
import os
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.environ.get("FX_VRP_WORK", os.path.dirname(HERE))
VD = os.path.join(WORK, "clean_v3", "vrp_v3")
OUTD = os.path.join(VD, "daily_panel_step11")
os.makedirs(OUTD, exist_ok=True)

df = pd.read_parquet(os.path.join(VD, "vrp_panel_v3.parquet"))
ok = df[df.rv_status == "ok"].copy()

# 6N anomaly extension (finalization finding): the structurally suspicious
# legacy 6N IV regime (30-40% prints with zero open interest against ~8%
# realized) persists through 2013, not just pre-2013 as previously excluded.
# 102 of 103 zero-OI IV>20% artifact days are 6N in 2013; high-IV days for
# other roots coincide with genuine stress (2011, Brexit, SNB de-peg, COVID).
# Rule: 6N enters the sample 2014-01-01.
n_drop = ((ok.economic_root == "6N") & (ok.date < "2014-01-01")).sum()
ok = ok[~((ok.economic_root == "6N") & (ok.date < "2014-01-01"))]
print(f"6N pre-2014 rows dropped: {n_drop:,}")

daily = (ok.groupby(["date", "economic_root", "target_tenor"], as_index=False)
           .agg(black76_iv=("black76_iv", "mean"),
                realized_vol=("realized_vol", "mean"),
                vrp_vol_spread=("vrp_vol_spread", "mean"),
                vrp_var=("vrp_var", "mean"),
                n_contracts=("black76_iv", "size"),
                open_interest=("open_interest", "sum")))
daily = daily.sort_values(["economic_root", "target_tenor", "date"],
                          kind="stable").reset_index(drop=True)
out = os.path.join(OUTD, "daily_vrp_panel_v3.parquet")
daily.to_parquet(out, index=False)

print(f"option-level ok rows: {len(ok):,}")
print(f"daily panel rows:     {len(daily):,}")
print(f"date range:           {daily.date.min().date()} .. {daily.date.max().date()}")
print(daily.groupby("target_tenor").size().to_string())
print(daily.groupby("economic_root").size().to_string())
