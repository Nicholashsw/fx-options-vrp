#!/usr/bin/env python3
"""Step 12: short-volatility strategy payoff proxies on the daily panel.

Payoff proxy per selected cell = vrp_vol_spread (IV minus forward RV, decimal).
Daily strategy payoff = equal-weight mean across selected cells that date.
These are payoff proxies, not executable P&L (no costs, hedging, margin).

IV z-score (leak-free): per (root, tenor), z_t = (IV_t - mu_t) / sd_t where
mu_t, sd_t are the rolling mean/std of the TRAILING 252 observations shifted
by one day (window ends at t-1; only information strictly prior to t is used),
minimum 126 observations. Cells with undefined z are excluded from
conditional strategies.

Twelve variants:
  static_all_roots_all_tenors, static_30d, static_60d, static_90d,
  static_ex_6N, static_major_roots_only (majors: 6E, 6B, 6J, 6S),
  signal_iv_zscore_ge_0, signal_iv_zscore_ge_0p5, signal_iv_zscore_ge_1,
  xs_top1/2/3_iv_z_by_date_tenor (per date and tenor, rank roots by z,
  take top N, then average across tenors).

Outputs: clean_v3/vrp_v3/strategy_step12/strategy_daily_payoff_proxy_v3.parquet
         clean_v3/vrp_v3/strategy_step12/strategy_summary_simple.csv
"""
import os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.environ.get("FX_VRP_WORK", os.path.dirname(HERE))
VD = os.path.join(WORK, "clean_v3", "vrp_v3")
OUTD = os.path.join(VD, "strategy_step12")
os.makedirs(OUTD, exist_ok=True)

MAJORS = ["6E", "6B", "6J", "6S"]
Z_WINDOW, Z_MIN = 252, 126

d = pd.read_parquet(os.path.join(VD, "daily_panel_step11",
                                 "daily_vrp_panel_v3.parquet"))
d = d.sort_values(["economic_root", "target_tenor", "date"], kind="stable")

# Leak-free trailing z-score: rolling window over obs t-252..t-1 (shift 1).
g = d.groupby(["economic_root", "target_tenor"], group_keys=False)
iv_lag_mean = g["black76_iv"].apply(
    lambda s: s.shift(1).rolling(Z_WINDOW, min_periods=Z_MIN).mean())
iv_lag_std = g["black76_iv"].apply(
    lambda s: s.shift(1).rolling(Z_WINDOW, min_periods=Z_MIN).std())
d["iv_z"] = (d["black76_iv"] - iv_lag_mean) / iv_lag_std

def daily_series(sel, name):
    s = (sel.groupby("date")["vrp_vol_spread"].mean()
            .rename("payoff").reset_index())
    s["strategy"] = name
    s["n_cells"] = sel.groupby("date").size().values
    return s

series = []
series.append(daily_series(d, "static_all_roots_all_tenors"))
for t in (30, 60, 90):
    series.append(daily_series(d[d.target_tenor == t], f"static_{t}d"))
series.append(daily_series(d[d.economic_root != "6N"], "static_ex_6N"))
series.append(daily_series(d[d.economic_root.isin(MAJORS)],
                           "static_major_roots_only"))

dz = d[d.iv_z.notna()]
for thr, tag in ((0.0, "ge_0"), (0.5, "ge_0p5"), (1.0, "ge_1")):
    series.append(daily_series(dz[dz.iv_z >= thr], f"signal_iv_zscore_{tag}"))

for n in (1, 2, 3):
    top = (dz.sort_values("iv_z", ascending=False)
             .groupby(["date", "target_tenor"], group_keys=False)
             .head(n))
    series.append(daily_series(top, f"xs_top{n}_iv_z_by_date_tenor"))

allp = pd.concat(series, ignore_index=True)
allp["payoff_volpts"] = allp["payoff"] * 100.0
allp.to_parquet(os.path.join(OUTD, "strategy_daily_payoff_proxy_v3.parquet"),
                index=False)

summ = (allp.groupby("strategy")["payoff_volpts"]
            .agg(n_days="size", mean="mean", median="median",
                 positive_pct=lambda s: 100.0 * (s > 0).mean(),
                 skew="skew", excess_kurtosis=pd.Series.kurt)
            .round(4))
summ.to_csv(os.path.join(OUTD, "strategy_summary_simple.csv"))
print(summ.to_string())
print("\nz-score coverage: %.1f%% of cells have valid z"
      % (100 * d.iv_z.notna().mean()))
