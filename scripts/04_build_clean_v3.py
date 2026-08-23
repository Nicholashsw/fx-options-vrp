#!/usr/bin/env python3
"""Step 3b: build clean_v3 monthly panel.
V3 source rule:
  month <  2017-07 : opt_old, all 7 roots
  month >= 2017-07 : opt_new (ADU/GBU/CAU/EUU/JPU/CHU -> 6A/6B/6C/6E/6J/6S)
                     + opt_old restricted to 6N
Futures joined from fut_defs/fut_stats throughout (same-month defs only).
Resumable with --budget; appends per-month metrics to clean_v3_build_log.csv.
"""
import argparse, os, tempfile, time
import pandas as pd
import pyarrow.parquet as pq_

WORK = os.environ.get("FX_VRP_WORK", os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
PQ = os.path.join(WORK, "parquet")
OUTD = os.path.join(WORK, "clean_v3", "panel_monthly")
LOG = os.path.join(WORK, "diagnostics", "clean_v3_build_log.csv")
CUTOFF = "2017-07"
NEW2ECO = {"ADU": "6A", "GBU": "6B", "CAU": "6C", "EUU": "6E",
           "JPU": "6J", "CHU": "6S"}
OLD_ROOTS = ["6A", "6B", "6C", "6E", "6J", "6N", "6S"]

def load_defs(role, month, classes, assets=None):
    d = pd.read_parquet(
        os.path.join(PQ, role, f"{month}.parquet"),
        columns=["ts_event", "instrument_id", "raw_symbol", "asset",
                 "instrument_class", "strike_price", "expiration",
                 "underlying_id"])
    d = d.sort_values(["instrument_id", "ts_event"], kind="stable")
    d = d.drop_duplicates("instrument_id", keep="last")
    d = d[d["instrument_class"].isin(classes)]
    if assets is not None:
        d = d[d["asset"].isin(assets)]
    return d.drop(columns=["ts_event"])

def load_stats(role, month, stat_types):
    path = os.path.join(PQ, role, f"{month}.parquet")
    t = pq_.read_table(path, columns=["ts_event", "ts_ref", "instrument_id",
                                      "stat_type", "price", "quantity"],
                       filters=[("stat_type", "in", list(stat_types))])
    s = t.to_pandas()
    del t
    ref = s["ts_ref"].fillna(s["ts_event"])
    s["date"] = pd.to_datetime(ref).dt.tz_convert("UTC").dt.date
    return s.drop(columns=["ts_ref", "ts_event"])

def one_source(month, defs_role, stats_role, assets, source_label):
    od = load_defs(defs_role, month, ["C", "P"], assets)
    st = load_stats(stats_role, month, (3, 9))
    setl = st[st.stat_type == 3].drop_duplicates(["date", "instrument_id"],
                                                 keep="last")
    oi = st[st.stat_type == 9].drop_duplicates(["date", "instrument_id"],
                                               keep="last")
    del st
    j = setl.rename(columns={"price": "option_settle"})[
        ["date", "instrument_id", "option_settle"]].merge(
        od, on="instrument_id", how="inner")
    j = j.merge(oi[["date", "instrument_id", "quantity"]].rename(
        columns={"quantity": "open_interest"}),
        on=["date", "instrument_id"], how="left")
    j["source_label"] = source_label
    j["economic_root"] = j["asset"].map(NEW2ECO).fillna(j["asset"])
    return j

def build_month(month):
    parts = []
    if month < CUTOFF:
        parts.append(one_source(month, "opt_old_defs", "opt_old_stats",
                                OLD_ROOTS, "old"))
    else:
        parts.append(one_source(month, "opt_new_defs", "opt_new_stats",
                                list(NEW2ECO), "new"))
        p = os.path.join(PQ, "opt_old_stats", f"{month}.parquet")
        if os.path.exists(p):
            parts.append(one_source(month, "opt_old_defs", "opt_old_stats",
                                    ["6N"], "old"))
    panel = pd.concat(parts, ignore_index=True)

    fd = load_defs("fut_defs", month, ["F"]).rename(columns={
        "instrument_id": "future_instrument_id", "raw_symbol": "future_symbol",
        "asset": "future_asset"})[["future_instrument_id", "future_symbol",
                                   "future_asset"]]
    fs = load_stats("fut_stats", month, (3,)).drop_duplicates(
        ["date", "instrument_id"], keep="last").rename(columns={
        "instrument_id": "future_instrument_id", "price": "future_settle"})
    panel = panel.merge(fd, left_on="underlying_id",
                        right_on="future_instrument_id", how="left")
    panel = panel.merge(fs[["date", "future_instrument_id", "future_settle"]],
                        on=["date", "future_instrument_id"], how="left")
    panel = panel.rename(columns={"instrument_class": "option_type"})
    panel["date"] = pd.to_datetime(panel["date"])
    panel["month"] = month
    cols = ["date", "instrument_id", "raw_symbol", "asset", "economic_root",
            "option_type", "strike_price", "expiration", "option_settle",
            "open_interest", "underlying_id", "future_instrument_id",
            "future_symbol", "future_asset", "future_settle", "source_label",
            "month"]
    panel = panel[cols]

    # metrics
    ndup = int(panel.duplicated(["date", "instrument_id", "source_label"]).sum())
    src_err = 0
    if month < CUTOFF:
        src_err = int((panel.source_label != "old").sum())
    else:
        src_err = int(((panel.source_label == "old")
                       & (panel.economic_root != "6N")).sum())
    fsym_miss = float(panel.future_symbol.isna().mean() * 100)
    fset_miss = float(panel.future_settle.isna().mean() * 100)
    spill = int((panel.date.dt.strftime("%Y-%m") != month).sum())
    roots = ",".join(sorted(panel.economic_root.unique()))

    tmp = os.path.join(tempfile.gettempdir(), f"panel_{month}.parquet")
    panel.to_parquet(tmp, index=False)
    import shutil
    final = os.path.join(OUTD, f"{month}.parquet")
    shutil.copyfile(tmp, final + ".w")
    os.replace(final + ".w", final)
    os.remove(tmp)
    return dict(month=month, rows=len(panel), dup_rows=ndup,
                source_rule_errors=src_err,
                future_symbol_missing_pct=round(fsym_miss, 4),
                future_settle_missing_pct=round(fset_miss, 4),
                date_spillover_rows=spill, roots=roots)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=float, default=30.0)
    a = ap.parse_args()
    t0 = time.time()
    os.makedirs(OUTD, exist_ok=True)

    months = sorted(f[:-8] for f in os.listdir(os.path.join(PQ, "fut_stats"))
                    if f.endswith(".parquet"))
    done = set()
    if os.path.exists(LOG):
        done = set(pd.read_csv(LOG)["month"].astype(str))
    todo = [m for m in months if m not in done]
    if not todo:
        print("ALL_DONE remaining=0"); return

    out, alerts = [], []
    for m in todo:
        if time.time() - t0 > a.budget:
            break
        r = build_month(m)
        out.append(r)
        if (r["dup_rows"] or r["source_rule_errors"]
                or r["future_settle_missing_pct"] > 1.0):
            alerts.append(r)
    if out:
        pd.DataFrame(out).to_csv(LOG, mode="a",
                                 header=not os.path.exists(LOG), index=False)
    for r in alerts:
        print("ALERT", r, flush=True)
    rem = len(todo) - len(out)
    print(("ALL_DONE" if rem == 0 else "PARTIAL")
          + f" built={len(out)} remaining={rem} elapsed={time.time()-t0:.0f}s")

if __name__ == "__main__":
    main()
