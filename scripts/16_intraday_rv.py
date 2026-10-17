#!/usr/bin/env python3
"""Step 16: forward realised volatility from intraday data, and two panels that
differ only in the realised-volatility estimator.

Step 10 measures forward volatility from daily settlement returns: about 21
squared returns for a 30-day option. That estimator is unbiased for variance but
noisy, and volatility is its square root, so the noise pulls realised volatility
down (Jensen) and pushes the IV - RV spread up, most at short tenors. Five-minute
returns over the same settlement-to-settlement sessions (q/, or scripts/
intraday_rv.py) measure the same variance far more precisely. This step puts the
two estimators side by side on identical option rows.

  python scripts/16_intraday_rv.py --export-panel     # 1. option rows for q/fwd_rv.q
  (run q/build_hdb.q, q/daily_rv.q, q/fwd_rv.q)        # 2. see q/README.md
  python scripts/16_intraday_rv.py                    # 3. build from the q output
  python scripts/16_intraday_rv.py --engine python    #    or compute it all in pandas instead
  python scripts/16_intraday_rv.py --check 2019-03    #    q against pandas for one month

Writes, under clean_v3/vrp_v3/:
  vrp_panel_v3_intraday.parquet       realized_vol from 5-minute returns
  vrp_panel_v3_settlematched.parquet  realized_vol from settlements, same ok rows
Both keep rv_status = ok only where both estimators are valid, so re-running
steps 11-13 on each (FX_VRP_VARIANT=intraday / settlematched) compares the
estimators on the same sample. Step 17 lines up the two strategy tables.

Aggregated diagnostics go to $FX_VRP_WORK/diagnostics/intraday_*.csv.
"""
import argparse
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import intraday_rv as irv  # noqa: E402

WORK = os.environ.get("FX_VRP_WORK", os.path.dirname(HERE))
VD = os.path.join(WORK, "clean_v3", "vrp_v3")
ID = os.path.join(WORK, "intraday")
DIAG = os.path.join(WORK, "diagnostics")
PANEL = os.path.join(VD, "vrp_panel_v3.parquet")
MIN_N5 = 100  # five-minute returns a session needs (of ~276 in 23 Globex hours)


def read_q_csv(path, dates=(), stamps=()):
    """Read a CSV written by q: dates as 2026.07.15, timestamps as 2026.07.15D19:00:00.000000000."""
    df = pd.read_csv(path)
    for c in dates:
        df[c] = pd.to_datetime(df[c], format="%Y.%m.%d")
    for c in stamps:
        df[c] = pd.to_datetime(df[c].str.replace("D", " ", regex=False), format="%Y.%m.%d %H:%M:%S.%f")
    return df


def read_bars(month):
    b = pd.read_csv(os.path.join(ID, "bars", f"{month}.csv"))
    b["time"] = pd.to_datetime(b["ts_ns"], unit="ns")
    return b.drop(columns="ts_ns")


def calendar():
    return pd.to_datetime(pd.read_csv(os.path.join(ID, "settle_calendar.csv"))["date"], format="%Y.%m.%d")


def daily_python(months):
    """q/daily_rv.q in pandas: each month with four days of lead-in from the month before."""
    cal, out, prev = calendar(), [], None
    for m in months:
        b = read_bars(m)
        start = pd.Period(m, "M").start_time
        x = b if prev is None else pd.concat([prev[prev["time"] >= start - pd.Timedelta(days=4)], b], ignore_index=True)
        d = irv.daily(x, cal)
        out.append(d[d["session"].dt.to_period("M") == pd.Period(m, "M")])
        prev = b
        print(f"{m}: {len(out[-1]):,} contract-sessions")
    return pd.concat(out, ignore_index=True)


def export_panel():
    p = pd.read_parquet(PANEL, columns=["date", "future_symbol", "target_tenor"])
    out = pd.DataFrame({"row_id": np.arange(len(p)), "date": pd.to_datetime(p["date"]).dt.strftime("%Y.%m.%d"),
                        "sym": p["future_symbol"], "tenor": p["target_tenor"].astype(int)})
    os.makedirs(ID, exist_ok=True)
    path = os.path.join(ID, "panel_for_q.csv")
    out.to_csv(path, index=False)
    print(f"{len(out):,} option rows -> {path}")


def check(month):
    """Recompute one month of rv_daily.csv and its forward windows in pandas and compare."""
    months = sorted(f[:-4] for f in os.listdir(os.path.join(ID, "bars")) if f.endswith(".csv"))
    i = months.index(month)
    want = daily_python(months[max(0, i - 1):i + 1])
    want = want[want["session"].dt.to_period("M") == pd.Period(month, "M")]
    got = read_q_csv(os.path.join(ID, "rv_daily.csv"), dates=["session"], stamps=["first_bar", "last_bar"])
    got = got[got["session"].dt.to_period("M") == pd.Period(month, "M")]
    j = want.merge(got, on=["sym", "session"], how="outer", suffixes=("_py", "_q"), indicator=True)
    print(f"{month}: {len(want):,} contract-sessions in pandas, {len(got):,} in q, "
          f"{(j['_merge'] == 'both').sum():,} in both")
    worst = {}
    for c in ["n5", "rv5", "bv5", "n1", "rv1", "volume"]:
        a, b = j[f"{c}_py"].astype(float), j[f"{c}_q"].astype(float)
        both = a.notna() & b.notna()
        worst[c] = float(((a - b).abs() / b.abs().clip(lower=1e-300))[both].max()) if both.any() else np.nan
        nulls = int((a.isna() != b.isna()).sum())
        print(f"  {c:<7} max relative difference {worst[c]:.2e}, null mismatches {nulls}")
    ok = (j["_merge"] == "both").all() and all(not (v > 1e-9) for v in worst.values())
    print("  daily: " + ("MATCH" if ok else "DIFFERENT"))

    p = pd.read_csv(os.path.join(ID, "panel_for_q.csv"))
    p["date"] = pd.to_datetime(p["date"], format="%Y.%m.%d")
    p = p[p["date"].dt.to_period("M") == pd.Period(month, "M")]
    fq = pd.read_csv(os.path.join(ID, "fwd_rv.csv"))
    fq = fq[fq["row_id"].isin(p["row_id"])]
    allq = read_q_csv(os.path.join(ID, "rv_daily.csv"), dates=["session"])
    fp = irv.forward(allq, p, MIN_N5)
    k = fp.merge(fq, on="row_id", suffixes=("_py", "_q"))
    same = (np.allclose(k["rv5_sum_py"], k["rv5_sum_q"], rtol=1e-9, atol=0)
            and (k["n_sessions_py"] == k["n_sessions_q"]).all())
    print(f"  forward windows: {len(k):,} option rows, " + ("MATCH" if same else "DIFFERENT"))


def build(engine):
    panel = pd.read_parquet(PANEL)
    if engine == "q":
        d = read_q_csv(os.path.join(ID, "rv_daily.csv"), dates=["session"], stamps=["first_bar", "last_bar"])
        f = pd.read_csv(os.path.join(ID, "fwd_rv.csv"))
    else:
        months = sorted(f[:-4] for f in os.listdir(os.path.join(ID, "bars")) if f.endswith(".csv"))
        d = daily_python(months)
        p = pd.DataFrame({"row_id": np.arange(len(panel)), "date": pd.to_datetime(panel["date"]),
                          "sym": panel["future_symbol"], "tenor": panel["target_tenor"].astype(int)})
        f = irv.forward(d, p, MIN_N5)
    f = f.set_index("row_id").reindex(np.arange(len(panel)))

    # an intraday window is usable on the step-10 rule: enough sessions for the tenor
    H = panel["target_tenor"].to_numpy(int)
    min_n = np.maximum(5, np.floor(0.5 * H * 5 / 7)).astype(int)
    intraday_ok = (f["n_sessions"].to_numpy() >= min_n) & f["rvol5"].notna().to_numpy()
    both_ok = (panel["rv_status"].to_numpy() == "ok") & intraday_ok
    print(f"option rows: {len(panel):,}; settlement RV ok {(panel['rv_status'] == 'ok').mean():.1%}; "
          f"intraday RV ok {intraday_ok.mean():.1%}; both {both_ok.mean():.1%}")

    status = np.where(both_ok, "ok", np.where(panel["rv_status"] == "ok", "no_intraday", panel["rv_status"]))
    matched = panel.assign(rv_status=status)
    intra = matched.copy()
    intra["realized_vol"] = np.where(both_ok, f["rvol5"].to_numpy(), np.nan)
    intra["realized_var"] = intra["realized_vol"] ** 2
    intra["vrp_var"] = intra["implied_var"] - intra["realized_var"]
    intra["vrp_vol_spread"] = intra["black76_iv"] - intra["realized_vol"]
    intra["rv_n_sessions"] = f["n_sessions"].to_numpy()
    intra["bipower_vol"] = np.sqrt(252 * f["bv5_sum"].to_numpy() / f["n_sessions"].where(f["n_sessions"] > 0).to_numpy())
    intra["rvol_1min"] = f["rvol1"].to_numpy()
    matched.to_parquet(os.path.join(VD, "vrp_panel_v3_settlematched.parquet"), index=False)
    intra.to_parquet(os.path.join(VD, "vrp_panel_v3_intraday.parquet"), index=False)
    print("wrote vrp_panel_v3_intraday.parquet and vrp_panel_v3_settlematched.parquet")
    diagnostics(d, panel[both_ok], intra[both_ok])


def diagnostics(d, settle_rows, intra_rows):
    os.makedirs(DIAG, exist_ok=True)

    # 1. one session at a time: the settlement return squared against the session's 5-minute variance
    r = pd.read_parquet(os.path.join(VD, "futures_returns.parquet"), columns=["future_symbol", "date", "r2"])
    r["date"] = pd.to_datetime(r["date"], utc=True).dt.tz_convert(None).dt.normalize()
    j = d[d["n5"] >= MIN_N5].merge(r, left_on=["sym", "session"], right_on=["future_symbol", "date"])
    per_root = j.groupby("root").agg(
        sessions=("rv5", "size"),
        mean_settle_r2_x1e4=("r2", lambda x: 1e4 * x.mean()),
        mean_rv5_x1e4=("rv5", lambda x: 1e4 * x.mean()),
        mean_rv1_x1e4=("rv1", lambda x: 1e4 * x.mean()),
        median_n5=("n5", "median"))
    per_root["rv5_over_settle"] = per_root["mean_rv5_x1e4"] / per_root["mean_settle_r2_x1e4"]
    per_root["rv1_over_rv5"] = per_root["mean_rv1_x1e4"] / per_root["mean_rv5_x1e4"]
    per_root["jump_share_of_rv5"] = j.groupby("root").apply(
        lambda g: float(np.clip(1 - g["bv5"] / g["rv5"], 0, None).mean()), include_groups=False)
    per_root["corr_log_rv5_log_settle_r2"] = j[j["r2"] > 0].groupby("root").apply(
        lambda g: float(np.corrcoef(np.log(g["rv5"]), np.log(g["r2"]))[0, 1]), include_groups=False)
    per_root.round(4).to_csv(os.path.join(DIAG, "intraday_daily_vs_settle.csv"))
    print("\n=== per session: settlement return squared vs 5-minute RV ===")
    print(per_root.round(3).to_string())

    # 2. the forward window, same option rows, both estimators
    def by(key):
        s = settle_rows.groupby(key)
        i = intra_rows.groupby(key)
        t = pd.DataFrame({
            "rows": s.size(),
            "iv_median_pct": 100 * s["black76_iv"].median(),
            "rv_settle_median_pct": 100 * s["realized_vol"].median(),
            "rv_intraday_median_pct": 100 * i["realized_vol"].median(),
            "spread_settle_median_pct": 100 * s["vrp_vol_spread"].median(),
            "spread_intraday_median_pct": 100 * i["vrp_vol_spread"].median(),
            "spread_settle_mean_pct": 100 * s["vrp_vol_spread"].mean(),
            "spread_intraday_mean_pct": 100 * i["vrp_vol_spread"].mean(),
            "vrp_var_settle_mean_x1e4": 1e4 * s["vrp_var"].mean(),
            "vrp_var_intraday_mean_x1e4": 1e4 * i["vrp_var"].mean(),
        })
        t["jensen_gap_pct"] = 100 * (np.sqrt(s["realized_var"].mean()) - s["realized_vol"].mean()) \
            - 100 * (np.sqrt(i["realized_var"].mean()) - i["realized_vol"].mean())
        return t.round(4)

    for key, name in [("economic_root", "root"), ("target_tenor", "tenor")]:
        t = by(key)
        t.to_csv(os.path.join(DIAG, f"intraday_vrp_by_{name}.csv"))
        print(f"\n=== forward window by {name}: settlement vs intraday RV, same option rows ===")
        print(t.to_string())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--export-panel", action="store_true")
    ap.add_argument("--engine", choices=["q", "python"], default="q")
    ap.add_argument("--check", metavar="YYYY-MM")
    a = ap.parse_args()
    if a.export_panel:
        export_panel()
    elif a.check:
        check(a.check)
    else:
        build(a.engine)


if __name__ == "__main__":
    main()
