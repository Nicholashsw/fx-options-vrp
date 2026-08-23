#!/usr/bin/env python3
"""Step 4: validate clean_v3 vs prior-laptop targets."""
import os, glob
import numpy as np
import pandas as pd

WORK = os.environ.get("FX_VRP_WORK", os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
PM = os.path.join(WORK, "clean_v3", "panel_monthly")
DIAG = os.path.join(WORK, "diagnostics")

log = pd.read_csv(os.path.join(DIAG, "clean_v3_build_log.csv")).sort_values("month")
print("=== build-log validation ===")
print(f" monthly files          = {len(log)}   (target 193)")
print(f" total rows             = {log.rows.sum():,}   (target 32,525,026)")
print(f" dup rows (in-month)    = {log.dup_rows.sum()}   (target 0)")
print(f" source rule errors     = {log.source_rule_errors.sum()}   (target 0)")
print(f" max future_symbol_missing_pct = {log.future_symbol_missing_pct.max()}   (target 0.0)")
print(f" max future_settle_missing_pct = {log.future_settle_missing_pct.max()}   (target ~0.086)")
print(f" months with settle missing >0: "
      f"{(log.future_settle_missing_pct>0).sum()}")
print(log.nlargest(5, 'future_settle_missing_pct')[
    ['month','rows','future_settle_missing_pct']].to_string(index=False))
print(f" date spillover rows total = {log.date_spillover_rows.sum():,}")

# rows by year x root + global cross-file duplicate check on keys
keys = []
yr_root = {}
for f in sorted(glob.glob(os.path.join(PM, "*.parquet"))):
    d = pd.read_parquet(f, columns=["date", "instrument_id", "source_label",
                                    "economic_root"])
    y = d["date"].dt.year
    for (yy, rr), c in d.groupby([y, "economic_root"]).size().items():
        yr_root[(yy, rr)] = yr_root.get((yy, rr), 0) + c
    keys.append(pd.DataFrame({
        "d": d["date"].values.astype("datetime64[D]").astype(np.int32),
        "i": d["instrument_id"].values.astype(np.int64),
        "s": (d["source_label"] == "new").values}))
k = pd.concat(keys, ignore_index=True)
del keys
ndup_global = int(k.duplicated().sum())
print(f"\n global dup (date,instrument,source) across all files = {ndup_global:,} "
      f"of {len(k):,}")
del k

t = pd.Series(yr_root).unstack(fill_value=0)
t.to_csv(os.path.join(DIAG, "clean_v3_rows_by_year_root.csv"))
print("\n=== rows by year x economic_root ===")
print(t.to_string())
missing_pairs = [(y, r) for y in range(2018, 2027) for r in
                 ["6A","6B","6C","6E","6J","6N","6S"] if yr_root.get((y, r), 0) == 0]
print("\n roots missing post-2018 year cells:", missing_pairs or "NONE (target: none)")
