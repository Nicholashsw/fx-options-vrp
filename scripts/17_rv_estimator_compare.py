#!/usr/bin/env python3
"""Step 17: the strategy table under each realised-volatility estimator.

After step 16, run steps 11-13 twice:

  FX_VRP_VARIANT=settlematched python scripts/11_daily_panel.py   (then 12, 13)
  FX_VRP_VARIANT=intraday      python scripts/11_daily_panel.py   (then 12, 13)

Both runs use the same option rows; only the forward realised volatility differs
(daily settlement returns vs five-minute returns). This step lines up their
twelve-strategy summaries and writes
$FX_VRP_WORK/diagnostics/strategy_by_rv_estimator.csv.
"""
import os

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.environ.get("FX_VRP_WORK", os.path.dirname(HERE))
VD = os.path.join(WORK, "clean_v3", "vrp_v3")
COLS = ["n_days", "mean", "median", "positive_pct", "skew", "t_nw63", "t_nonoverlap21"]


def load(variant):
    p = os.path.join(VD, f"robust_stats_step13_{variant}", "robust_strategy_summary_v3.csv")
    if not os.path.exists(p):
        raise SystemExit(f"missing {p}: run steps 11-13 with FX_VRP_VARIANT={variant}")
    return pd.read_csv(p).set_index("strategy")[COLS]


s, i = load("settlematched"), load("intraday")
out = s.join(i, lsuffix="_settle", rsuffix="_intraday")
out["mean_change"] = out["mean_intraday"] - out["mean_settle"]
out["t_nw63_change"] = out["t_nw63_intraday"] - out["t_nw63_settle"]
os.makedirs(os.path.join(WORK, "diagnostics"), exist_ok=True)
path = os.path.join(WORK, "diagnostics", "strategy_by_rv_estimator.csv")
out.round(4).to_csv(path)
view = out[["mean_settle", "mean_intraday", "median_settle", "median_intraday",
            "t_nw63_settle", "t_nw63_intraday", "positive_pct_settle", "positive_pct_intraday"]]
print("payoff proxies in vol points per day, same option rows\n")
print(view.round(3).to_string())
print(f"\nwrote {path}")
