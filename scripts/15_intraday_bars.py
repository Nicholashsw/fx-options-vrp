#!/usr/bin/env python3
"""Step 15: one-minute futures bars for the intraday realised-volatility leg.

Pulls Databento GLBX.MDP3 ohlcv-1m for the seven futures roots, a month at a time,
maps each instrument_id to its contract (e.g. 6EZ3) with the step-1 futures
definitions of the same month, and writes one CSV per month for q/build_hdb.q:

  $FX_VRP_WORK/intraday/raw/YYYY-MM.ohlcv-1m.dbn.zst   the download, kept
  $FX_VRP_WORK/intraday/bars/YYYY-MM.csv               ts_ns,sym,root,close,volume

ts_ns is the bar's CLOSE: Databento stamps the open, so a minute is added. Each
month is requested as bars opening from one minute before the month to one minute
before the next, so every file holds exactly the bars that close in its month
and no UTC date is split across two files.

Also writes intraday/settle_calendar.csv, the dates on which the futures settled
(from step 9), which the q side uses as session boundaries.

  python scripts/15_intraday_bars.py --plan                    # cost per month, nothing downloaded
  python scripts/15_intraday_bars.py --budget 30 --max-cost 40 # resumable; stops at the budget
  python scripts/15_intraday_bars.py --calendar                # just the settlement calendar

Needs DATABENTO_API_KEY. The --max-cost guard (US$) is checked against
Databento's quote for each month before it is pulled.
"""
import argparse
import os
import sys
import time

import pandas as pd

WORK = os.environ.get("FX_VRP_WORK", os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
PQ = os.path.join(WORK, "parquet")
OUT = os.path.join(WORK, "intraday")
RAW = os.path.join(OUT, "raw")
BARS = os.path.join(OUT, "bars")
SETTLES = os.path.join(WORK, "clean_v3", "vrp_v3", "futures_settle_daily.parquet")

DATASET = "GLBX.MDP3"
SCHEMA = "ohlcv-1m"
ROOTS = ["6A", "6B", "6C", "6E", "6J", "6N", "6S"]
FIRST, LAST = "2010-06", "2026-06"
MINUTE = pd.Timedelta(minutes=1)


def months():
    return [str(p) for p in pd.period_range(FIRST, LAST, freq="M")]


def window(month):
    start = pd.Period(month, "M").start_time - MINUTE
    end = (pd.Period(month, "M") + 1).start_time - MINUTE
    return start.strftime("%Y-%m-%dT%H:%M:%SZ"), end.strftime("%Y-%m-%dT%H:%M:%SZ")


def query(month):
    start, end = window(month)
    return dict(dataset=DATASET, schema=SCHEMA, symbols=[f"{r}.FUT" for r in ROOTS],
                stype_in="parent", start=start, end=end)


def contract_map(month):
    """instrument_id -> (raw_symbol, root) from the step-1 definitions, as step 9 does."""
    frames = []
    for m in {month, str(pd.Period(month, "M") - 1)}:  # a bar opening a minute early can need last month's ids
        p = os.path.join(PQ, "fut_defs", f"{m}.parquet")
        if os.path.exists(p):
            frames.append(pd.read_parquet(p, columns=["ts_event", "instrument_id", "raw_symbol", "asset",
                                                      "instrument_class"]))
    if not frames:
        sys.exit(f"no futures definitions for {month} under {PQ}/fut_defs (run steps 0-1 first)")
    d = pd.concat(frames).sort_values(["instrument_id", "ts_event"], kind="stable")
    d = d[d.instrument_class == "F"].drop_duplicates("instrument_id", keep="last")
    return d.set_index("instrument_id")[["raw_symbol", "asset"]]


def export(month, store):
    df = store.to_df(price_type="float", pretty_ts=False, map_symbols=False).reset_index()
    if df.empty:
        return 0, 0
    ids = contract_map(month)
    df = df.join(ids, on="instrument_id", how="inner")
    out = pd.DataFrame({
        "ts_ns": df["ts_event"].astype("int64") + MINUTE.value,
        "sym": df["raw_symbol"],
        "root": df["asset"],
        "close": df["close"],
        "volume": df["volume"].astype("int64"),
    })
    out = out[out["root"].isin(ROOTS)].sort_values(["ts_ns", "sym"], kind="stable")
    tmp = os.path.join(BARS, f"{month}.csv.w")
    out.to_csv(tmp, index=False)
    os.replace(tmp, os.path.join(BARS, f"{month}.csv"))
    return len(out), out["sym"].nunique()


def calendar():
    if not os.path.exists(SETTLES):
        sys.exit(f"missing {SETTLES} (run step 9 first)")
    d = pd.read_parquet(SETTLES, columns=["date"])
    cal = pd.DataFrame({"date": sorted(pd.to_datetime(d["date"], utc=True).dt.tz_convert(None).dt.normalize().unique())})
    cal["date"] = cal["date"].dt.strftime("%Y.%m.%d")
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, "settle_calendar.csv")
    cal.to_csv(path, index=False)
    print(f"settlement calendar: {len(cal):,} dates -> {path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true", help="print Databento's cost per month and stop")
    ap.add_argument("--budget", type=float, default=30.0, help="minutes to spend before stopping")
    ap.add_argument("--max-cost", type=float, default=40.0, help="refuse any month quoted above this (US$)")
    ap.add_argument("--calendar", action="store_true", help="only write the settlement calendar")
    a = ap.parse_args()

    calendar()
    if a.calendar:
        return

    import databento as db
    key = os.environ.get("DATABENTO_API_KEY")
    if not key:
        sys.exit("DATABENTO_API_KEY is not set")
    client = db.Historical(key)
    os.makedirs(RAW, exist_ok=True)
    os.makedirs(BARS, exist_ok=True)

    todo = [m for m in months() if not os.path.exists(os.path.join(BARS, f"{m}.csv"))]
    if a.plan:
        total = 0.0
        for m in todo:
            c = client.metadata.get_cost(**query(m))
            total += c
            print(f"{m}  US${c:8.2f}")
        print(f"{len(todo)} months to pull, US${total:.2f} in total")
        return

    t0, n = time.time(), 0
    for m in todo:
        if time.time() - t0 > a.budget * 60:
            break
        q = query(m)
        cost = client.metadata.get_cost(**q)
        if cost > a.max_cost:
            sys.exit(f"{m}: quoted US${cost:.2f}, above --max-cost {a.max_cost:.2f}; stopping")
        raw = os.path.join(RAW, f"{m}.{SCHEMA}.dbn.zst")
        store = db.DBNStore.from_file(raw) if os.path.exists(raw) else client.timeseries.get_range(**q, path=raw)
        rows, syms = export(m, store)
        print(f"{m}: US${cost:.2f}, {rows:,} bars, {syms} contracts")
        n += 1
    rem = len(todo) - n
    print(("ALL_DONE" if rem == 0 else "PARTIAL") + f" months={n} remaining={rem} elapsed={time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
