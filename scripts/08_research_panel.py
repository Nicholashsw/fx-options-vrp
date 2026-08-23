#!/usr/bin/env python3
"""Step 7: research IV panel.
keep iv_status in (ok, ok_near_intrinsic); 1% <= IV <= 80%;
drop 6N before 2013-01-01. Save research_iv_panel_v3.parquet."""
import os
import pandas as pd

WORK = os.environ.get("FX_VRP_WORK", os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
IV = os.path.join(WORK, "clean_v3", "iv_v3", "iv_panel_v3.parquet")
OUTD = os.path.join(WORK, "clean_v3", "iv_v3", "research_panel")
OUT = os.path.join(OUTD, "research_iv_panel_v3.parquet")
DIAG = os.path.join(WORK, "diagnostics")

os.makedirs(OUTD, exist_ok=True)
df = pd.read_parquet(IV)
n0 = len(df)
df = df[df.iv_status.isin(["ok", "ok_near_intrinsic"])]
n1 = len(df)
df = df[(df.black76_iv >= 0.01) & (df.black76_iv <= 0.80)]
n2 = len(df)
early_6n = (df.economic_root == "6N") & (df.date < "2013-01-01")
n_drop_6n = int(early_6n.sum())
df = df[~early_6n]
n3 = len(df)
df = df.reset_index(drop=True)
df.to_parquet(OUT, index=False)

print(f"original rows       = {n0:,}   (target 440,467)")
print(f"after valid IV      = {n1:,}   (target 440,462)")
print(f"after IV 1%..80%    = {n2:,}   (target 440,440)")
print(f"dropped early 6N    = {n_drop_6n:,}   (target 9,810)")
print(f"final research rows = {n3:,}   (target 430,630)")

tgt_rows = {"6A": 63798, "6B": 63798, "6C": 63798, "6E": 63784,
            "6J": 63798, "6N": 47868, "6S": 63786}
tgt_med = {"6A": 9.824358, "6B": 7.969980, "6C": 6.997066, "6E": 7.530896,
           "6J": 9.048753, "6N": 9.308838, "6S": 7.695687}
g = df.groupby("economic_root")
rows = g.size()
med = 100 * g["black76_iv"].median()
print("\nroot   rows (target)        median IV% (target)")
for r in sorted(tgt_rows):
    print(f"  {r}: {rows[r]:>7,} ({tgt_rows[r]:>7,})   "
          f"{med[r]:.6f} ({tgt_med[r]:.6f})  "
          f"{'OK' if rows[r]==tgt_rows[r] and abs(med[r]-tgt_med[r])<5e-7 else 'DIFF'}")
pd.DataFrame({"rows": rows, "rows_target": pd.Series(tgt_rows),
              "median_iv_pct": med, "median_target": pd.Series(tgt_med)}
             ).to_csv(os.path.join(DIAG, "research_panel_vs_targets.csv"))
