#!/usr/bin/env python3
"""Step 13: robust inference for the strategy payoff proxies.

Forward RV windows overlap across consecutive dates, so daily payoff series
are strongly serially correlated. Inference:
  1. Newey-West t-statistics on the mean at lags 5, 21, 63
     (regression on a constant with HAC standard errors).
  2. Non-overlapping sampling: every 21st observation at offsets 0..20;
     simple t-statistic per offset; report the mean t across offsets.

Output: clean_v3/vrp_v3/robust_stats_step13/robust_strategy_summary_v3.csv
"""
import os
import numpy as np
import pandas as pd
import statsmodels.api as sm

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.environ.get("FX_VRP_WORK", os.path.dirname(HERE))
VD = os.path.join(WORK, "clean_v3", "vrp_v3")
SFX = f"_{os.environ['FX_VRP_VARIANT']}" if os.environ.get("FX_VRP_VARIANT") else ""  # see step 11
OUTD = os.path.join(VD, "robust_stats_step13" + SFX)
os.makedirs(OUTD, exist_ok=True)

allp = pd.read_parquet(os.path.join(VD, "strategy_step12" + SFX,
                                    "strategy_daily_payoff_proxy_v3.parquet"))

def nw_t(y, lag):
    y = np.asarray(y, float)
    X = np.ones((len(y), 1))
    res = sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": lag})
    return float(res.tvalues[0])

def nonoverlap_t(y, step=21):
    y = np.asarray(y, float)
    ts = []
    for off in range(step):
        s = y[off::step]
        if len(s) > 10 and s.std(ddof=1) > 0:
            ts.append(s.mean() / (s.std(ddof=1) / np.sqrt(len(s))))
    return float(np.mean(ts)), len(ts)

rows = []
for strat, g in allp.groupby("strategy"):
    y = g.sort_values("date")["payoff_volpts"].to_numpy()
    no_t, no_k = nonoverlap_t(y)
    rows.append({
        "strategy": strat,
        "n_days": len(y),
        "mean": y.mean(),
        "median": np.median(y),
        "positive_pct": 100.0 * (y > 0).mean(),
        "skew": pd.Series(y).skew(),
        "excess_kurtosis": pd.Series(y).kurt(),
        "t_naive": y.mean() / (y.std(ddof=1) / np.sqrt(len(y))),
        "t_nw5": nw_t(y, 5),
        "t_nw21": nw_t(y, 21),
        "t_nw63": nw_t(y, 63),
        "t_nonoverlap21": no_t,
        "nonoverlap_offsets": no_k,
    })

ORDER = ["static_all_roots_all_tenors", "static_30d", "static_60d",
         "static_90d", "static_ex_6N", "static_major_roots_only",
         "signal_iv_zscore_ge_0", "signal_iv_zscore_ge_0p5",
         "signal_iv_zscore_ge_1", "xs_top1_iv_z_by_date_tenor",
         "xs_top2_iv_z_by_date_tenor", "xs_top3_iv_z_by_date_tenor"]
out = pd.DataFrame(rows).set_index("strategy").loc[ORDER].round(4)
out.to_csv(os.path.join(OUTD, "robust_strategy_summary_v3.csv"))
print(out.to_string())
