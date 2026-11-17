"""Step 12: short-volatility payoff proxies on the daily panel."""
import os
import pandas as pd

from fxvrp.config import out_dir
from fxvrp.signals import iv_zscore

MAJORS = ["6E", "6B", "6J", "6S"]


def daily_series(sel, name):
    s = (sel.groupby("date")["vrp_vol_spread"].mean()
            .rename("payoff").reset_index())
    s["strategy"] = name
    s["n_cells"] = sel.groupby("date").size().values
    return s


def run():
    # Payoff proxy per selected cell = vrp_vol_spread (IV minus forward RV,
    # decimal). Daily strategy payoff = equal-weight mean across selected cells
    # that date. These are payoff proxies, not executable P&L.
    # Cells with undefined z are excluded from conditional strategies.
    # Majors: 6E, 6B, 6J, 6S. The xs_top variants rank roots by z per date and
    # tenor, take the top N, then average across tenors.
    daily_dir = out_dir("daily_panel_step11")
    OUTD = out_dir("strategy_step12")

    d = pd.read_parquet(os.path.join(daily_dir, "daily_vrp_panel_v3.parquet"))
    d = d.sort_values(["economic_root", "target_tenor", "date"], kind="stable")

    d["iv_z"] = iv_zscore(d)

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

    # Aggregates only: daily mean payoff of the static proxy and the top-1 rule.
    (allp[allp.strategy.isin(["static_all_roots_all_tenors", "xs_top1_iv_z_by_date_tenor"])]
        .pivot(index="date", columns="strategy", values="payoff_volpts")
        .rename(columns={"static_all_roots_all_tenors": "static",
                         "xs_top1_iv_z_by_date_tenor": "xs_top1"})
        [["static", "xs_top1"]].round(6)
        .to_csv(os.path.join(OUTD, "strategy_daily_payoff.csv")))

    summ = (allp.groupby("strategy")["payoff_volpts"]
                .agg(n_days="size", mean="mean", median="median",
                     positive_pct=lambda s: 100.0 * (s > 0).mean(),
                     skew="skew", excess_kurtosis=pd.Series.kurt)
                .round(4))
    summ.to_csv(os.path.join(OUTD, "strategy_summary_simple.csv"))
    print(summ.to_string())
    print("\nz-score coverage: %.1f%% of cells have valid z"
          % (100 * d.iv_z.notna().mean()))
