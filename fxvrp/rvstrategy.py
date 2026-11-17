"""Step 16: cross-sectional short-vol rule ranked by forecast-based VRP.

Predicted VRP per cell = black76_iv - exp(model log-RV forecast) from step 15.
Rules mirror step 12's xs_top1: per (date, tenor) short the single root with
the highest signal, payoff proxy = realised vrp_vol_spread of that cell,
daily payoff = mean across tenors; dates with no position drop out.

  ml_top1_<m>       highest predicted VRP, m in HAR, HAR_IV, XGB, LSTM, SHUF
  ml_top1_pos_<m>   same pick, kept only if predicted VRP > 0
  xs_top1_iv_z      baseline: highest trailing IV z-score, same cells

All series use the step-15 out-of-sample universe (every cell has iv_z and
every forecast), so ml_top1_* and xs_top1_iv_z share the same date set. Each
ml_top1_pos_* is also compared with xs_top1_iv_z on its own dates. Inference
reuses nw_t and nonoverlap_t from step 13. Design: docs/ML_PREREG.md.

Outputs: clean_v3/vrp_v3/ml_step16/
  ml_strategy_daily_v3.parquet   daily payoff series
  ml_strategy_summary.csv        mean/median/hit/NW t/non-overlap t/moments
  ml_strategy_by_year.csv        mean and days per calendar year
  ml_strategy_paired.csv         variant minus baseline, common dates
  ml_2_cumulative_payoff.png
"""
import os
import numpy as np
import pandas as pd

from fxvrp import stats as rs
from fxvrp.config import vrp_dir, out_dir
from fxvrp.signals import iv_zscore
from fxvrp.strategy import daily_series
ML_MODELS = ["HAR", "HAR_IV", "XGB", "LSTM", "SHUF"]
BASE = "xs_top1_iv_z"


def top1(d, col):
    order = {r: i for i, r in enumerate(sorted(d.economic_root.unique()))}
    return (d.assign(_r=d.economic_root.map(order))
             .sort_values(["date", "target_tenor", col, "_r"],
                          ascending=[True, True, False, True], kind="stable")
             .groupby(["date", "target_tenor"], group_keys=False).head(1)
             .drop(columns="_r"))


def check_step12_baseline(VD):
    """The step-12 xs_top1 rule, recomputed here, must match the published
    series exactly on the full step-11 sample."""
    d = pd.read_parquet(os.path.join(VD, "daily_panel_step11",
                                     "daily_vrp_panel_v3.parquet"))
    d = d.sort_values(["economic_root", "target_tenor", "date"],
                      kind="stable")
    d["iv_z"] = iv_zscore(d)
    dz = d[d.iv_z.notna()]
    top = (dz.sort_values("iv_z", ascending=False)
             .groupby(["date", "target_tenor"], group_keys=False).head(1))
    mine = daily_series(top, "x").set_index("date")["payoff"] * 100.0
    pub = pd.read_parquet(os.path.join(VD, "strategy_step12",
                                       "strategy_daily_payoff_proxy_v3.parquet"))
    pub = (pub[pub.strategy == "xs_top1_iv_z_by_date_tenor"]
           .set_index("date")["payoff_volpts"])
    pd.testing.assert_series_equal(mine.sort_index(), pub.sort_index(),
                                   check_names=False, check_exact=True)
    return pub


def summarise(name, s):
    s = s.sort_values("date")
    y = s["payoff_volpts"].to_numpy()
    ex = s[s.date.dt.year != 2022]["payoff_volpts"].to_numpy()
    no_t, no_k = rs.nonoverlap_t(y)
    return {"strategy": name, "n_days": len(y),
            "first_date": s.date.min().date(), "last_date": s.date.max().date(),
            "mean": y.mean(), "median": np.median(y),
            "positive_pct": 100.0 * (y > 0).mean(),
            "t_nw5": rs.nw_t(y, 5), "t_nw21": rs.nw_t(y, 21),
            "t_nw63": rs.nw_t(y, 63), "t_nonoverlap21": no_t,
            "nonoverlap_offsets": no_k,
            "skew": pd.Series(y).skew(),
            "excess_kurtosis": pd.Series(y).kurt(),
            "mean_ex2022": ex.mean(), "t_nw63_ex2022": rs.nw_t(ex, 63),
            "n_days_ex2022": len(ex)}


def paired(name, a, b, base_name):
    m = a.merge(b, on="date", suffixes=("_a", "_b"))
    dlt = (m.payoff_volpts_a - m.payoff_volpts_b).to_numpy()
    ex = m.date.dt.year != 2022
    return {"strategy": name, "baseline": base_name, "n_days": len(m),
            "mean_variant": m.payoff_volpts_a.mean(),
            "mean_baseline": m.payoff_volpts_b.mean(),
            "mean_diff": dlt.mean(), "t_nw63_diff": rs.nw_t(dlt, 63),
            "t_nw63_variant": rs.nw_t(m.payoff_volpts_a.to_numpy(), 63),
            "t_nw63_baseline": rs.nw_t(m.payoff_volpts_b.to_numpy(), 63),
            "same_pick_pct": np.nan,
            "mean_diff_ex2022": dlt[ex].mean(),
            "t_nw63_diff_ex2022": rs.nw_t(dlt[ex], 63)}


def chart(series, OUTD):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"figure.dpi": 200, "savefig.dpi": 200,
                         "font.size": 9, "axes.grid": True,
                         "grid.alpha": 0.3, "axes.axisbelow": True})
    cols = {BASE: "#000000", "ml_top1_HAR": "#1f77b4",
            "ml_top1_HAR_IV": "#2ca02c", "ml_top1_XGB": "#d62728",
            "ml_top1_LSTM": "#9467bd", "ml_top1_SHUF": "#bcbd22"}
    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    for name, c in cols.items():
        s = series[name].sort_values("date")
        ax.plot(s.date, s.payoff_volpts.cumsum(), color=c, lw=1.6 if
                name == BASE else 1.0, label=name)
    ax.set_ylabel("Cumulative payoff proxy, vol points")
    ax.set_title("Top-1 short-vol rule: IV z-score vs forecast-based VRP, "
                 "out-of-sample", fontsize=10)
    ax.legend(fontsize=7, ncol=2)
    fig.text(0.01, 0.01, "Payoff proxy: ex-post IV minus forward RV of "
             "selected positions. Excludes transaction costs, hedging, and "
             "margin.", fontsize=6.5)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(os.path.join(OUTD, "ml_2_cumulative_payoff.png"))
    plt.close(fig)


def run():
    VD = vrp_dir()
    OUTD = out_dir("ml_step16")
    pub = check_step12_baseline(VD)
    print("step-12 xs_top1 reproduced exactly on the full sample")

    f = pd.read_parquet(os.path.join(VD, "ml_step15",
                                     "rv_forecasts_v3.parquet"))
    for m in ML_MODELS:
        f[f"pvrp_{m}"] = f.black76_iv - np.exp(f[f"pred_{m}"])

    picks = {BASE: top1(f, "iv_z")}
    for m in ML_MODELS:
        t = top1(f, f"pvrp_{m}")
        picks[f"ml_top1_{m}"] = t
        picks[f"ml_top1_pos_{m}"] = t[t[f"pvrp_{m}"] > 0]
    series = {}
    for name, sel in picks.items():
        s = daily_series(sel, name)
        s["payoff_volpts"] = s["payoff"] * 100.0
        series[name] = s
    oos = f.date.min()
    pub_oos = pub[pub.index >= oos].rename("payoff_volpts").reset_index()
    pub_oos["strategy"] = "step12_xs_top1_iv_z_published_oos"
    series[pub_oos.strategy.iloc[0]] = pub_oos

    order = ([BASE, "step12_xs_top1_iv_z_published_oos"]
             + [f"ml_top1_{m}" for m in ML_MODELS]
             + [f"ml_top1_pos_{m}" for m in ML_MODELS])
    summ = pd.DataFrame([summarise(n, series[n]) for n in order])
    summ = summ.set_index("strategy")

    base_picks = picks[BASE].set_index(["date", "target_tenor"]).economic_root
    prs = []
    for m in ML_MODELS:
        for name in (f"ml_top1_{m}", f"ml_top1_pos_{m}"):
            row = paired(name, series[name], series[BASE], BASE)
            mp = picks[name].set_index(["date", "target_tenor"]).economic_root
            row["same_pick_pct"] = 100.0 * (
                mp == base_picks.reindex(mp.index)).mean()
            prs.append(row)
    prs = pd.DataFrame(prs).set_index("strategy")

    allp = pd.concat([series[n].assign(strategy=n) for n in order],
                     ignore_index=True)
    allp.to_parquet(os.path.join(OUTD, "ml_strategy_daily_v3.parquet"),
                    index=False)
    yr = (allp.assign(year=allp.date.dt.year)
              .groupby(["strategy", "year"])["payoff_volpts"]
              .agg(mean="mean", n_days="size").reset_index())
    yr.round(4).to_csv(os.path.join(OUTD, "ml_strategy_by_year.csv"),
                       index=False)
    summ.round(4).to_csv(os.path.join(OUTD, "ml_strategy_summary.csv"))
    prs.round(4).to_csv(os.path.join(OUTD, "ml_strategy_paired.csv"))
    chart(series, OUTD)

    pd.set_option("display.width", 250)
    print(f"\nOOS universe: {len(f):,} cells, {f.date.nunique():,} dates")
    print("\n=== summary ===")
    print(summ.drop(columns=["first_date", "last_date",
                             "nonoverlap_offsets"]).round(4).to_string())
    print("\n=== paired vs xs_top1_iv_z ===")
    print(prs.drop(columns="baseline").round(4).to_string())
    print("\n=== mean by year ===")
    print(yr.pivot(index="year", columns="strategy", values="mean")[order]
            .round(3).to_string())

