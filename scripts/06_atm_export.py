#!/usr/bin/env python3
"""Step 5: ATM 30/60/90 export.
Per month: filter (option_settle>0, future_settle>0, strike>0, 10<=dte<=130),
per target tenor (30/60/90): tenor_diff<=15, |log moneyness|<=0.10,
top 3 per (date, economic_root, target_tenor, option_type) ranked by
tenor_diff asc, abs_log_moneyness asc, open_interest_rank_value desc.
Then GLOBAL dedup by (date, instrument_id, source_label, target_tenor)
[月-boundary spillover], global rerank, keep top 3, final dup check = 0.
Phase 1 (--budget loop): monthly picks -> picks CSV. Phase 2 (--finalize).
"""
import argparse, os, time
import numpy as np
import pandas as pd

WORK = os.environ.get("FX_VRP_WORK", os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
PM = os.path.join(WORK, "clean_v3", "panel_monthly")
OUTD = os.path.join(WORK, "clean_v3", "atm_export_v3")
PICKS = os.path.join(OUTD, "monthly_picks.csv")
FINAL = os.path.join(OUTD, "atm_panel_v3.parquet")
DIAG = os.path.join(WORK, "diagnostics")
TENORS = (30, 60, 90)

RANK_KEYS = ["tenor_diff", "abs_log_moneyness", "neg_oi_rank", "instrument_id"]
GRP = ["date", "economic_root", "target_tenor", "option_type"]

def month_picks(month):
    df = pd.read_parquet(os.path.join(PM, f"{month}.parquet"))
    df = df[(df.option_settle > 0) & (df.future_settle > 0)
            & (df.strike_price > 0)].copy()
    exp_day = df["expiration"].dt.tz_convert("UTC").dt.normalize().dt.tz_localize(None)
    df["dte"] = (exp_day - df["date"]).dt.days
    df = df[(df.dte >= 10) & (df.dte <= 130)]
    df["log_moneyness"] = np.log(df.strike_price / df.future_settle)
    df["abs_log_moneyness"] = df.log_moneyness.abs()
    df = df[df.abs_log_moneyness <= 0.10]
    df["open_interest_rank_value"] = df.open_interest.fillna(-1.0)
    df["neg_oi_rank"] = -df.open_interest_rank_value
    # each row -> nearest target tenor; boundary ties go to the OUTER tenor
    # (dte<=45 -> 30, 45<dte<75 -> 60, dte>=75 -> 90), then tenor_diff<=15
    df["target_tenor"] = np.select(
        [df.dte <= 45, df.dte < 75], [30, 60], default=90)
    df["tenor_diff"] = (df.dte - df.target_tenor).abs()
    df = df[df.tenor_diff <= 15]
    if df.empty:
        return pd.DataFrame()
    df = df.sort_values(GRP + RANK_KEYS, kind="stable")
    df["rank"] = df.groupby(GRP).cumcount() + 1
    r = df[df["rank"] <= 3].copy()
    r["panel_month"] = month
    return r.drop(columns=["neg_oi_rank"])

def finalize():
    df = pd.read_csv(PICKS, parse_dates=["date", "expiration"])
    n0 = len(df)
    df = df.sort_values(["date", "instrument_id", "source_label", "target_tenor",
                         "panel_month"], kind="stable")
    df = df.drop_duplicates(["date", "instrument_id", "source_label",
                             "target_tenor"], keep="last")
    n1 = len(df)
    df["neg_oi_rank"] = -df.open_interest_rank_value
    df = df.sort_values(GRP + RANK_KEYS, kind="stable")
    df["rank"] = df.groupby(GRP).cumcount() + 1
    df = df[df["rank"] <= 3].drop(columns=["neg_oi_rank"])
    n2 = len(df)

    dup_final = int(df.duplicated(GRP + ["rank"]).sum())
    q_fail = int(((df.option_settle <= 0) | (df.future_settle <= 0)
                  | (df.strike_price <= 0) | (df.tenor_diff > 15)
                  | (df.abs_log_moneyness > 0.10)
                  | (df.dte < 10) | (df.dte > 130)).sum())
    df = df.sort_values(["date", "economic_root", "target_tenor",
                         "option_type", "rank"]).reset_index(drop=True)
    df.to_parquet(FINAL, index=False)

    print(f"picks rows              = {n0:,}")
    print(f"after global dedup      = {n1:,}  (removed {n0-n1:,} spillover dups)")
    print(f"after global rerank top3= {n2:,}   (target 440,467)")
    print(f"date range              = {df.date.min().date()} .. {df.date.max().date()}"
          f"   (target 2010-06-04 .. 2026-06-26)")
    print(f"dups by date/root/tenor/type/rank = {dup_final}   (target 0)")
    print(f"quality failures        = {q_fail}   (target 0)")
    print("\nrows by root (target 63798/63798/63798/63786/63798/57703/63786):")
    print(df.economic_root.value_counts().sort_index().to_string())
    print("\nrows by tenor (target 30:157579 60:151002 90:131886):")
    print(df.target_tenor.value_counts().sort_index().to_string())
    s = df.groupby("economic_root").size().rename("rows").reset_index()
    s.to_csv(os.path.join(DIAG, "atm_export_rows_by_root.csv"), index=False)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=float, default=30.0)
    ap.add_argument("--finalize", action="store_true")
    a = ap.parse_args()
    os.makedirs(OUTD, exist_ok=True)
    if a.finalize:
        finalize(); return
    t0 = time.time()
    months = sorted(f[:-8] for f in os.listdir(PM) if f.endswith(".parquet"))
    done = set()
    if os.path.exists(PICKS) and os.path.getsize(PICKS) > 0:
        done = set(pd.read_csv(PICKS, usecols=["panel_month"])
                   ["panel_month"].astype(str))
    todo = [m for m in months if m not in done]
    if not todo:
        print("ALL_DONE remaining=0"); return
    n = 0
    for m in todo:
        if time.time() - t0 > a.budget:
            break
        p = month_picks(m)
        if len(p):
            hdr = not (os.path.exists(PICKS) and os.path.getsize(PICKS) > 0)
            p.to_csv(PICKS, mode="a", header=hdr, index=False)
        n += 1
    rem = len(todo) - n
    print(("ALL_DONE" if rem == 0 else "PARTIAL")
          + f" months={n} remaining={rem} elapsed={time.time()-t0:.0f}s")

if __name__ == "__main__":
    main()
