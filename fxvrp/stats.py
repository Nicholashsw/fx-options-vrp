"""Step 13: Newey-West and non-overlapping t-statistics for the payoff proxies."""
import os
import numpy as np
import pandas as pd
import statsmodels.api as sm

from fxvrp.config import out_dir

ORDER = ["static_all_roots_all_tenors", "static_30d", "static_60d",
         "static_90d", "static_ex_6N", "static_major_roots_only",
         "signal_iv_zscore_ge_0", "signal_iv_zscore_ge_0p5",
         "signal_iv_zscore_ge_1", "xs_top1_iv_z_by_date_tenor",
         "xs_top2_iv_z_by_date_tenor", "xs_top3_iv_z_by_date_tenor"]


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


def run():
    # Forward RV windows overlap across consecutive dates, so the daily payoff
    # series are strongly serially correlated. Inference: Newey-West t on the
    # mean at lags 5, 21, 63, and every 21st observation at offsets 0..20 with
    # a simple t per offset, reporting the mean t across offsets.
    OUTD = out_dir("robust_stats_step13")

    allp = pd.read_parquet(os.path.join(out_dir("strategy_step12"),
                                        "strategy_daily_payoff_proxy_v3.parquet"))

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

    out = pd.DataFrame(rows).set_index("strategy").loc[ORDER].round(4)
    out.to_csv(os.path.join(OUTD, "robust_strategy_summary_v3.csv"))
    print(out.to_string())
