#!/usr/bin/env python3
"""Step 2: coverage audit. Per role/month: rows by stat_type, ids, and
settlement/OI attribution to roots via that month's deduped definitions.
Resumable (appends to CSVs, skips processed role-months)."""
import argparse, os, time
import pandas as pd

WORK = os.environ.get("FX_VRP_WORK", os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
PQ = os.path.join(WORK, "parquet")
DIAG = os.path.join(WORK, "diagnostics")
STATS_CSV = os.path.join(DIAG, "coverage_stats_monthly.csv")
ROOTS_CSV = os.path.join(DIAG, "coverage_roots_monthly.csv")

NEW2ECO = {"ADU": "6A", "GBU": "6B", "CAU": "6C", "EUU": "6E", "JPU": "6J", "CHU": "6S"}
PAIRS = {"opt_old_stats": "opt_old_defs", "opt_new_stats": "opt_new_defs",
         "fut_stats": "fut_defs"}

def defs_dedup(role, month):
    p = os.path.join(PQ, role, f"{month}.parquet")
    d = pd.read_parquet(p, columns=["ts_event", "instrument_id", "asset",
                                    "instrument_class", "security_type"])
    d = d.sort_values(["instrument_id", "ts_event"]).drop_duplicates(
        "instrument_id", keep="last")
    if role == "fut_defs":
        good = d["instrument_class"] == "F"
    else:
        good = d["instrument_class"].isin(["C", "P"])
    d["eligible"] = good
    return d[["instrument_id", "asset", "eligible"]]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=float, default=30.0)
    a = ap.parse_args()
    t0 = time.time()

    done = set()
    if os.path.exists(STATS_CSV):
        prev = pd.read_csv(STATS_CSV)
        done = set(zip(prev["role"], prev["month"]))

    work = []
    for role in PAIRS:
        for f in sorted(os.listdir(os.path.join(PQ, role))):
            if f.endswith(".parquet"):
                m = f[:-8]
                if (role, m) not in done:
                    work.append((role, m))
    if not work:
        print("ALL_DONE remaining=0"); return

    stats_rows, roots_rows, n = [], [], 0
    for role, month in work:
        if time.time() - t0 > a.budget:
            break
        s = pd.read_parquet(os.path.join(PQ, role, f"{month}.parquet"),
                            columns=["instrument_id", "stat_type"])
        vc = s["stat_type"].value_counts()
        row = dict(role=role, month=month, rows_total=len(s),
                   rows_settle=int(vc.get(3, 0)), rows_oi=int(vc.get(9, 0)),
                   rows_bid=int(vc.get(8, 0)), rows_ask=int(vc.get(7, 0)),
                   rows_other=int(len(s) - vc.get(3, 0) - vc.get(9, 0)
                                  - vc.get(8, 0) - vc.get(7, 0)))
        st = s[s["stat_type"].isin([3, 9])]
        d = defs_dedup(PAIRS[role], month)
        j = st.merge(d, on="instrument_id", how="left")
        row["settle_ids"] = int(st.loc[st.stat_type == 3, "instrument_id"].nunique())
        row["settle_unmatched_defs_pct"] = round(
            100 * float(j.loc[j.stat_type == 3, "asset"].isna().mean() or 0), 4)
        stats_rows.append(row)
        je = j[j["eligible"] == True]  # noqa: E712
        g = je.groupby(["asset", "stat_type"]).size().unstack(fill_value=0)
        for asset, r in g.iterrows():
            eco = NEW2ECO.get(asset, asset)
            if role == "opt_new_stats" and asset not in NEW2ECO:
                continue  # stray non-target products (WA1, 4EU...)
            roots_rows.append(dict(role=role, month=month, asset=asset,
                                   eco_root=eco, settle_rows=int(r.get(3, 0)),
                                   oi_rows=int(r.get(9, 0))))
        n += 1

    pd.DataFrame(stats_rows).to_csv(STATS_CSV, mode="a",
                                    header=not os.path.exists(STATS_CSV), index=False)
    pd.DataFrame(roots_rows).to_csv(ROOTS_CSV, mode="a",
                                    header=not os.path.exists(ROOTS_CSV), index=False)
    rem = len(work) - n
    print(("ALL_DONE" if rem == 0 else "PARTIAL")
          + f" processed={n} remaining={rem} elapsed={time.time()-t0:.0f}s")

if __name__ == "__main__":
    main()
