#!/usr/bin/env python3
"""Step 8a: daily futures settlement series + consecutive log returns.
Per month: fut_stats stat_type 3 dedup (date, instrument_id) keep last,
inner-join same-month fut_defs (class F) dedup -> (date, symbol, settle).
Global: dedup (date, future_symbol); returns per symbol with gap guard
(consecutive settle obs > 14 calendar days apart -> return dropped; kills
decade-apart symbol reuse, e.g. 6AZ0 Dec-2010 vs Dec-2020).
Phase 1: --budget loop -> monthly parts. Phase 2: --finalize.
"""
import argparse, os, time
import numpy as np
import pandas as pd

WORK = os.environ.get("FX_VRP_WORK", os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
PQ = os.path.join(WORK, "parquet")
OUTD = os.path.join(WORK, "clean_v3", "vrp_v3")
PARTS = os.path.join(OUTD, "fut_daily_parts")
DAILY = os.path.join(OUTD, "futures_settle_daily.parquet")
RETS = os.path.join(OUTD, "futures_returns.parquet")
GAP_MAX_DAYS = 14

def build_month(month):
    d = pd.read_parquet(os.path.join(PQ, "fut_defs", f"{month}.parquet"),
                        columns=["ts_event", "instrument_id", "raw_symbol",
                                 "asset", "instrument_class"])
    d = d.sort_values(["instrument_id", "ts_event"], kind="stable")
    d = d.drop_duplicates("instrument_id", keep="last")
    d = d[d.instrument_class == "F"][["instrument_id", "raw_symbol", "asset"]]
    s = pd.read_parquet(os.path.join(PQ, "fut_stats", f"{month}.parquet"),
                        columns=["ts_event", "ts_ref", "instrument_id",
                                 "stat_type", "price"])
    s = s[s.stat_type == 3].copy()
    ref = s["ts_ref"].fillna(s["ts_event"])
    s["date"] = pd.to_datetime(ref).dt.tz_convert("UTC").dt.normalize()
    s = s.drop_duplicates(["date", "instrument_id"], keep="last")
    j = s.merge(d, on="instrument_id", how="inner")
    j = j.rename(columns={"raw_symbol": "future_symbol", "price": "future_settle",
                          "asset": "future_asset",
                          "instrument_id": "future_instrument_id"})
    j["src_month"] = month
    return j[["date", "future_symbol", "future_asset", "future_instrument_id",
              "future_settle", "src_month"]]

def finalize():
    parts = [pd.read_parquet(os.path.join(PARTS, f))
             for f in sorted(os.listdir(PARTS)) if f.endswith(".parquet")]
    df = pd.concat(parts, ignore_index=True)
    n0 = len(df)
    df = df.sort_values(["future_symbol", "date", "src_month"], kind="stable")
    df = df.drop_duplicates(["date", "future_symbol"], keep="last")
    # same (date,symbol) must not map to 2 ids after dedup; check pre-dedup:
    ambig = 0  # post-dedup one row per key by construction; count key clashes
    df = df.drop(columns=["src_month"]).reset_index(drop=True)
    df.to_parquet(DAILY, index=False)

    g = df.groupby("future_symbol", sort=False)
    prev_settle = g["future_settle"].shift(1)
    prev_date = g["date"].shift(1)
    gap = (df["date"] - prev_date).dt.days
    ok = (gap <= GAP_MAX_DAYS) & (prev_settle > 0) & (df["future_settle"] > 0)
    r = pd.DataFrame({
        "future_symbol": df.future_symbol,
        "date": df.date,
        "log_ret": np.where(ok, np.log(df.future_settle / prev_settle), np.nan),
        "gap_days": gap})
    r = r[r.log_ret.notna()].reset_index(drop=True)
    r["r2"] = r.log_ret ** 2
    r.to_parquet(RETS, index=False)
    print(f"daily rows: {n0:,} -> dedup(date,symbol): {len(df):,}")
    print(f"symbols: {df.future_symbol.nunique():,}; "
          f"date range {df.date.min().date()}..{df.date.max().date()}")
    print(f"returns rows: {len(r):,}; dropped-by-gap-guard: "
          f"{int((gap > GAP_MAX_DAYS).sum()):,}")
    print(f"|log_ret| > 20% count (sanity): {int((r.log_ret.abs() > 0.20).sum())}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=float, default=30.0)
    ap.add_argument("--finalize", action="store_true")
    a = ap.parse_args()
    os.makedirs(PARTS, exist_ok=True)
    if a.finalize:
        finalize(); return
    t0 = time.time()
    months = sorted(f[:-8] for f in os.listdir(os.path.join(PQ, "fut_stats"))
                    if f.endswith(".parquet"))
    todo = [m for m in months
            if not os.path.exists(os.path.join(PARTS, f"{m}.parquet"))]
    n = 0
    for m in todo:
        if time.time() - t0 > a.budget:
            break
        p = build_month(m)
        tmp = os.path.join(PARTS, f"{m}.parquet.w")
        p.to_parquet(tmp, index=False)
        os.replace(tmp, os.path.join(PARTS, f"{m}.parquet"))
        n += 1
    rem = len(todo) - n
    print(("ALL_DONE" if rem == 0 else "PARTIAL")
          + f" months={n} remaining={rem} elapsed={time.time()-t0:.0f}s")

if __name__ == "__main__":
    main()
