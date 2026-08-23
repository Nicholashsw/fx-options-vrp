#!/usr/bin/env python3
"""Step 3a: join diagnostic on benchmark months, replicating the exact V3
dedup+join recipe. Targets from the prior laptop:
  2016-01 old all roots : defs_dedup=7,241  settle_rows=121,044  fut_missing=0.0
  2024-01 new migrated  : defs_dedup=11,992 settle_rows=233,574  fut_missing=0.0
  2024-01 old 6N only   : defs_dedup=484    settle_rows=8,818    fut_missing=0.0
"""
import os
import pandas as pd

WORK = os.environ.get("FX_VRP_WORK", os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
PQ = os.path.join(WORK, "parquet")
NEW_ASSETS = {"ADU", "GBU", "CAU", "EUU", "JPU", "CHU"}

def load_defs(role, month, classes, assets=None):
    d = pd.read_parquet(
        os.path.join(PQ, role, f"{month}.parquet"),
        columns=["ts_event", "instrument_id", "raw_symbol", "asset",
                 "instrument_class", "strike_price", "expiration",
                 "underlying_id", "underlying"])
    d = d.sort_values(["instrument_id", "ts_event"], kind="stable")
    d = d.drop_duplicates("instrument_id", keep="last")
    d = d[d["instrument_class"].isin(classes)]
    if assets is not None:
        d = d[d["asset"].isin(assets)]
    return d

def load_stats(role, month, stat_type):
    s = pd.read_parquet(
        os.path.join(PQ, role, f"{month}.parquet"),
        columns=["ts_event", "ts_ref", "instrument_id", "stat_type",
                 "price", "quantity"])
    s = s[s["stat_type"] == stat_type].copy()
    ref = s["ts_ref"].fillna(s["ts_event"])
    s["date"] = pd.to_datetime(ref).dt.tz_convert("UTC").dt.date
    s = s.drop_duplicates(["date", "instrument_id"], keep="last")  # file order
    return s

def diagnose(label, month, opt_defs_role, opt_stats_role, assets):
    od = load_defs(opt_defs_role, month, ["C", "P"], assets)
    fd = load_defs("fut_defs", month, ["F"]).rename(columns={
        "instrument_id": "future_instrument_id", "raw_symbol": "future_symbol",
        "asset": "future_asset"})[["future_instrument_id", "future_symbol",
                                   "future_asset"]]
    os_ = load_stats(opt_stats_role, month, 3)
    oi = load_stats(opt_stats_role, month, 9)
    fs = load_stats("fut_stats", month, 3).rename(columns={
        "instrument_id": "future_instrument_id", "price": "future_settle"})

    # option settle -> option defs (inner: only defined C/P in-scope options)
    j = os_.merge(od, on="instrument_id", how="inner", suffixes=("", "_d"))
    # -> future defs via underlying_id
    j = j.merge(fd, left_on="underlying_id", right_on="future_instrument_id",
                how="left")
    fut_sym_missing = j["future_symbol"].isna().mean() * 100
    # -> future settle by (date, future_instrument_id)
    j = j.merge(fs[["date", "future_instrument_id", "future_settle"]],
                on=["date", "future_instrument_id"], how="left")
    fut_settle_missing = j["future_settle"].isna().mean() * 100
    # OI join (left)
    j = j.merge(oi[["date", "instrument_id", "quantity"]].rename(
        columns={"quantity": "open_interest"}),
        on=["date", "instrument_id"], how="left")

    print(f"===== {label} ({month}) =====")
    print(f" option defs dedup (C/P in-scope) = {len(od):,}")
    print(f" option settle rows dedup(all ids) = {len(os_):,}")
    print(f" option settle rows joined to defs = {len(j):,}")
    print(f" future_symbol missing pct  = {fut_sym_missing:.4f}")
    print(f" future_settle missing pct  = {fut_settle_missing:.4f}")
    print(f" OI present pct             = {100 - j['open_interest'].isna().mean()*100:.2f}")
    print(f" join row explosion check: settle_joined/settle_dedup = "
          f"{len(j)/max(len(os_),1):.4f} (must be <= 1)")
    return j

if __name__ == "__main__":
    diagnose("2016-01 OLD all roots", "2016-01", "opt_old_defs", "opt_old_stats",
             ["6A", "6B", "6C", "6E", "6J", "6N", "6S"])
    diagnose("2024-01 NEW migrated roots", "2024-01", "opt_new_defs",
             "opt_new_stats", sorted(NEW_ASSETS))
    diagnose("2024-01 OLD 6N only", "2024-01", "opt_old_defs", "opt_old_stats",
             ["6N"])
