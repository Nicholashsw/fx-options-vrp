"""Step 14: publication charts and tables 1-4."""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from fxvrp.config import out_dir
from fxvrp.stats import ORDER

# --- shared chart style (identical in every repo's figures.py) ---------------------------
# Palette: first three categorical slots of the validated reference palette (pass all-pairs
# CVD checks in light mode). Ink and grid are text tokens, never series colours.
import matplotlib as mpl
import matplotlib.pyplot as plt

SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"

STYLE = ({
    "font.family": "DejaVu Sans", "font.size": 10,
    "axes.titlesize": 11, "axes.titleweight": "regular", "axes.titlelocation": "left",
    "axes.labelsize": 9.5, "axes.labelcolor": INK2, "axes.edgecolor": INK2, "axes.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "axes.grid.axis": "y", "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.facecolor": SURFACE, "figure.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "xtick.color": INK2, "ytick.color": INK2, "xtick.labelsize": 9, "ytick.labelsize": 9,
    "xtick.major.size": 0, "ytick.major.size": 0, "lines.linewidth": 2,
    "legend.frameon": False, "figure.dpi": 100, "savefig.dpi": 200,
})
FIGSIZE = (7.2, 4.0)   # one hero size for all six projects


def finish(fig, ax, title, subtitle, path):
    """Title (what the chart says) and subtitle (what is plotted, from which file), then save."""
    ax.set_title(title, color=INK, pad=22)
    ax.text(0, 1.02, subtitle, transform=ax.transAxes, color=INK2, fontsize=8.5, va="bottom")
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
# -------------------------------------------------------------------------------------------


ROOT_COLORS = {"6A": "#1f77b4", "6B": "#ff7f0e", "6C": "#2ca02c",
               "6E": "#d62728", "6J": "#9467bd", "6N": "#8c564b",
               "6S": "#17becf"}
ROOT_NAMES = {"6A": "AUD", "6B": "GBP", "6C": "CAD", "6E": "EUR",
              "6J": "JPY", "6N": "NZD", "6S": "CHF"}
FOOT = ("Payoff proxy: ex-post IV minus forward RV of selected positions. "
        "Excludes transaction costs, hedging, and margin.")


def run():
    # Charts are 200 DPI with consistent root colors and payoff-proxy footnotes
    # on the strategy charts.
    CD = out_dir("charts_step14")
    TD = out_dir("tables_step14")
    plt.rcParams.update({"figure.dpi": 200, "savefig.dpi": 200,
                         "font.size": 9, "axes.grid": True,
                         "grid.alpha": 0.3, "axes.axisbelow": True})

    daily = pd.read_parquet(os.path.join(out_dir("daily_panel_step11"),
                                         "daily_vrp_panel_v3.parquet"))
    allp = pd.read_parquet(os.path.join(out_dir("strategy_step12"),
                                        "strategy_daily_payoff_proxy_v3.parquet"))
    rob = pd.read_csv(os.path.join(out_dir("robust_stats_step13"),
                                   "robust_strategy_summary_v3.csv"),
                      index_col=0)

    roots = ["6A", "6B", "6C", "6E", "6J", "6N", "6S"]
    lab = [f"{r}\n({ROOT_NAMES[r]})" for r in roots]

    # ---- Table 1 + Chart 1/2: by root -----------------------------------------
    t1 = (daily.groupby("economic_root")[["black76_iv", "realized_vol",
                                          "vrp_vol_spread"]].median() * 100)
    t1.columns = ["median_iv", "median_rv", "median_vrp_spread"]
    t1 = t1.round(4).loc[roots]
    t1.to_csv(os.path.join(TD, "table_1_vrp_by_root.csv"))

    x = np.arange(len(roots)); w = 0.38
    fig, ax = plt.subplots(figsize=(7.0, 3.6))
    ax.bar(x - w/2, t1.median_iv, w, label="Implied (Black-76 ATM)",
           color="#3b6ea5")
    ax.bar(x + w/2, t1.median_rv, w, label="Forward realized",
           color="#c8873a")
    ax.set_xticks(x, lab); ax.set_ylabel("Annualized volatility, %")
    ax.set_title("Median Implied vs Forward Realized Volatility by FX Root, "
                 "2010-2026 (6N from 2014)")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(os.path.join(CD, "chart_1_iv_vs_rv_by_root.png")); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.0, 3.6))
    ax.bar(x, t1.median_vrp_spread, color=[ROOT_COLORS[r] for r in roots])
    ax.axhline(0, color="k", lw=0.8)
    ax.set_xticks(x, lab); ax.set_ylabel("Median IV-RV spread, vol points")
    ax.set_title("Median Volatility Risk Premium by FX Root, 2010-2026 "
                 "(6N from 2014)")
    fig.tight_layout()
    fig.savefig(os.path.join(CD, "chart_2_vrp_by_root.png")); plt.close(fig)

    # ---- Table 2 + Chart 3: by tenor -------------------------------------------
    t2 = daily.groupby("target_tenor").agg(
        median_vrp_spread=("vrp_vol_spread", lambda s: 100 * s.median()),
        positive_pct=("vrp_vol_spread", lambda s: 100 * (s > 0).mean()),
        n_obs=("vrp_vol_spread", "size")).round(4)
    t2.to_csv(os.path.join(TD, "table_2_vrp_by_tenor.csv"))

    fig, ax = plt.subplots(figsize=(5.2, 3.4))
    xt = np.arange(3)
    ax.bar(xt, t2.median_vrp_spread, 0.55, color="#3b6ea5")
    for i, (m, p) in enumerate(zip(t2.median_vrp_spread, t2.positive_pct)):
        ax.text(i, m + 0.01, f"{m:.2f}\n({p:.1f}% > 0)", ha="center", fontsize=8)
    ax.set_xticks(xt, ["30d", "60d", "90d"])
    ax.set_ylabel("Median IV-RV spread, vol points")
    ax.set_title("Median Volatility Risk Premium by Target Tenor")
    ax.set_ylim(0, t2.median_vrp_spread.max() * 1.35)
    fig.tight_layout()
    fig.savefig(os.path.join(CD, "chart_3_vrp_by_tenor.png")); plt.close(fig)

    # ---- Table 4 + Chart 4: yearly heatmap -------------------------------------
    daily["year"] = daily.date.dt.year
    t4 = (daily.pivot_table(index="year", columns="economic_root",
                            values="vrp_vol_spread", aggfunc="median") * 100
          ).round(4)[roots]
    t4.to_csv(os.path.join(TD, "table_4_yearly_median_vrp_by_root.csv"))

    fig, ax = plt.subplots(figsize=(7.0, 4.6))
    vmax = np.nanmax(np.abs(t4.values))
    im = ax.imshow(t4.values, aspect="auto", cmap="RdBu_r",
                   vmin=-vmax, vmax=vmax)
    ax.set_xticks(range(len(roots)), lab, fontsize=8)
    ax.set_yticks(range(len(t4)), t4.index, fontsize=8)
    for i in range(t4.shape[0]):
        for j in range(t4.shape[1]):
            v = t4.values[i, j]
            if np.isfinite(v):
                ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=6.5,
                        color="white" if abs(v) > 0.6 * vmax else "black")
    fig.colorbar(im, ax=ax, label="Median IV-RV spread, vol points")
    ax.set_title("Yearly Median Volatility Risk Premium by FX Root")
    fig.tight_layout()
    fig.savefig(os.path.join(CD, "chart_4_yearly_vrp_heatmap.png")); plt.close(fig)

    # ---- Table 3 + Chart 5: strategies -----------------------------------------
    t3 = rob[["n_days", "mean", "median", "positive_pct", "skew",
              "excess_kurtosis", "t_nw63", "t_nonoverlap21"]].round(4)
    t3.to_csv(os.path.join(TD, "table_3_strategy_robust_summary.csv"))

    show = ORDER
    short = ["static all", "static 30d", "static 60d", "static 90d",
             "static ex-6N", "static majors", "signal z>=0", "signal z>=0.5",
             "signal z>=1", "xs top-1", "xs top-2", "xs top-3"]
    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    xs = np.arange(len(show)); w = 0.38
    ax.bar(xs - w/2, rob.loc[show, "mean"], w, label="Mean", color="#3b6ea5")
    ax.bar(xs + w/2, rob.loc[show, "median"], w, label="Median",
           color="#c8873a")
    for i, s in enumerate(show):
        ax.text(i, max(rob.loc[s, "mean"], rob.loc[s, "median"]) + 0.02,
                f"t={rob.loc[s, 't_nw63']:.2f}", ha="center", fontsize=7)
    ax.set_xticks(xs, short, rotation=40, ha="right", fontsize=8)
    ax.set_ylabel("Daily payoff proxy, vol points")
    ax.set_title("Strategy Payoff Proxies with Newey-West (63-lag) t-statistics")
    ax.legend(frameon=False)
    fig.text(0.01, 0.005, FOOT, fontsize=6.5, style="italic")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(os.path.join(CD, "chart_5_strategy_summary.png")); plt.close(fig)

    # ---- Chart 6: cumulative payoff proxy --------------------------------------
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    for s, c, l in [("static_all_roots_all_tenors", "#3b6ea5", "Static, all roots and tenors"),
                    ("signal_iv_zscore_ge_0p5", "#2ca02c", "Time-series signal, z >= 0.5"),
                    ("xs_top1_iv_z_by_date_tenor", "#d62728", "Cross-sectional top-1 IV z")]:
        g = allp[allp.strategy == s].sort_values("date")
        ax.plot(g.date, g.payoff_volpts.cumsum(), color=c, lw=1.1, label=l)
    ax.axhline(0, color="k", lw=0.8)
    ax.set_ylabel("Cumulative payoff proxy (vol points)")
    ax.set_title("Cumulative Payoff Proxy: Static vs High-IV Conditioning")
    ax.legend(frameon=False, fontsize=8)
    fig.text(0.01, 0.005, FOOT, fontsize=6.5, style="italic")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(os.path.join(CD, "chart_6_cumulative_payoff.png")); plt.close(fig)

    # ---- Chart 7: IV time series (context) -------------------------------------
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    p30 = daily[daily.target_tenor == 30]
    for r in roots:
        g = p30[p30.economic_root == r].sort_values("date")
        ax.plot(g.date, 100 * g.black76_iv.rolling(21, min_periods=5).median(),
                color=ROOT_COLORS[r], lw=0.9, label=f"{r} ({ROOT_NAMES[r]})")
    ax.set_ylabel("Annualized volatility, %")
    ax.set_title("ATM Implied Volatility, 30d Tenor (21-day rolling median)")
    ax.legend(frameon=False, fontsize=7, ncol=4)
    fig.tight_layout()
    fig.savefig(os.path.join(CD, "chart_7_iv_timeseries_30d.png")); plt.close(fig)

    print("charts ->", CD)
    print("tables ->", TD)
    print(t1.to_string()); print(t2.to_string()); print(t3.to_string())


def hero(out_dir_="figures"):
    """Hero chart: cumulative payoff of the top-1 short-vol rule vs static (committed daily file)."""
    with mpl.rc_context(STYLE):
        _hero(out_dir_)


def _hero(out_dir_):
    d = pd.read_csv(os.path.join("results", "strategy_daily_payoff.csv"),
                    index_col=0, parse_dates=True).loc["2013-01-01":]
    cum = d.fillna(0).cumsum()   # xs_top1 starts Dec 2010, so it has no gaps after 2013
    fig, ax = plt.subplots(figsize=FIGSIZE)
    ax.axvspan(pd.Timestamp("2022-01-01"), pd.Timestamp("2022-12-31"), color=GRID, alpha=0.7, lw=0)
    ax.plot(cum.index, cum.xs_top1, color=BLUE)
    ax.plot(cum.index, cum.static, color=ORANGE)
    end = cum.index[-1]
    for col, c, name in [("xs_top1", BLUE, "Top-1 by IV z-score"), ("static", ORANGE, "Static short vol")]:
        ax.annotate(f"{name}\n{cum[col].iloc[-1]:,.0f}", (end, cum[col].iloc[-1]),
                    xytext=(6, 0), textcoords="offset points", color=c, fontsize=9, va="center",
                    annotation_clip=False)
    ax.set_xlim(cum.index[0], end + pd.Timedelta(days=900))
    ax.set_xticks([pd.Timestamp(f"{y}-01-01") for y in range(2014, 2027, 2)],
                  [str(y) for y in range(2014, 2027, 2)])
    ax.text(pd.Timestamp("2022-07-01"), -230, "2022", color=INK2, fontsize=9, ha="center")
    ax.set_ylabel("Cumulative payoff proxy, vol points")
    finish(fig, ax, "Selling vol only in the richest currency earned more than always selling it",
           "Daily payoff summed from 2013; static series starts 2010-06 "
           "(strategy_daily_payoff.csv)",
           os.path.join(out_dir_, "hero.png"))


if __name__ == "__main__":
    import sys
    if "--hero" in sys.argv:
        hero()
    else:
        run()
