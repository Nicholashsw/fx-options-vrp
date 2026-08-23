#!/usr/bin/env python3
"""Build and execute the analysis notebook vrp_analysis.ipynb.

The notebook reproduces every headline table and chart of the paper from the
step-10 option-level VRP panel onward. It does not rerun the raw-data pipeline.
"""
import os
import nbformat as nbf
from nbclient import NotebookClient

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.environ.get("FX_VRP_WORK", os.path.dirname(HERE))
OUT = os.path.join(WORK, "notebooks")
os.makedirs(OUT, exist_ok=True)

nb = nbf.v4.new_notebook()
md = nbf.v4.new_markdown_cell
code = nbf.v4.new_code_cell
C = []

C.append(md("""# Volatility Risk Premia in CME G10 FX Options on Futures
### Analysis notebook

Nicholas Hong, Nanyang Technological University

This notebook reproduces every headline table and figure of the paper from the
option-level VRP panel (`clean_v3/vrp_v3/vrp_panel_v3.parquet`, output of
pipeline step 10). It covers: the daily panel aggregation (step 11), leak-free
strategy payoff proxies (step 12), robust inference (step 13), and all charts
and tables (step 14).

**Wording note:** all strategy results are payoff proxies (ex-post implied
minus forward realized volatility of selected positions), not executable P&L.
Transaction costs, delta hedging, and margin are excluded.

**Data prerequisites:** the pipeline through step 10 must have been run; see
`README.md` and `scripts/00_inventory.py` .. `scripts/10_vrp.py`."""))

C.append(code("""import os
import numpy as np
import pandas as pd
import statsmodels.api as sm
import matplotlib.pyplot as plt

WORK = os.path.abspath(os.path.join(os.getcwd(), ".."))
VD = os.path.join(WORK, "clean_v3", "vrp_v3")
plt.rcParams.update({"figure.dpi": 110, "font.size": 9, "axes.grid": True,
                     "grid.alpha": 0.3, "axes.axisbelow": True})
ROOT_COLORS = {"6A": "#1f77b4", "6B": "#ff7f0e", "6C": "#2ca02c",
               "6E": "#d62728", "6J": "#9467bd", "6N": "#8c564b",
               "6S": "#17becf"}
ROOT_NAMES = {"6A": "AUD", "6B": "GBP", "6C": "CAD", "6E": "EUR",
              "6J": "JPY", "6N": "NZD", "6S": "CHF"}
ROOTS = list(ROOT_COLORS)"""))

C.append(md("""## 1. Load the option-level VRP panel (step 10 output)

Each row is one selected near-ATM option on one date, with Black-76 implied
volatility and the forward realized volatility of its own underlying futures
contract over the matching tenor horizon."""))

C.append(code("""panel = pd.read_parquet(os.path.join(VD, "vrp_panel_v3.parquet"))
print(f"rows: {len(panel):,}   dates: {panel.date.min().date()} .. {panel.date.max().date()}")
print(panel.rv_status.value_counts().to_dict())
panel.head(3)"""))

C.append(md("""## 2. Daily panel (step 11)

Keep `rv_status == 'ok'` rows, apply the 6N anomaly exclusion (6N enters
2014-01-01; the structurally suspicious legacy 6N IV regime of 30-40% prints
on zero-open-interest contracts persists through 2013), and aggregate
equal-weight to (date, root, tenor)."""))

C.append(code("""ok = panel[panel.rv_status == "ok"]
ok = ok[~((ok.economic_root == "6N") & (ok.date < "2014-01-01"))]
daily = (ok.groupby(["date", "economic_root", "target_tenor"], as_index=False)
           .agg(black76_iv=("black76_iv", "mean"),
                realized_vol=("realized_vol", "mean"),
                vrp_vol_spread=("vrp_vol_spread", "mean"),
                open_interest=("open_interest", "sum")))
daily = daily.sort_values(["economic_root", "target_tenor", "date"]).reset_index(drop=True)
print(f"daily panel rows: {len(daily):,}")"""))

C.append(md("""## 3. Table 1 and Table 2: the premium by root and tenor"""))

C.append(code("""t1 = (daily.groupby("economic_root")[["black76_iv", "realized_vol", "vrp_vol_spread"]]
       .median() * 100).round(2)
t1.columns = ["median_iv", "median_rv", "median_vrp_spread"]
t1"""))

C.append(code("""t2 = daily.groupby("target_tenor").agg(
    median_vrp_spread=("vrp_vol_spread", lambda s: round(100 * s.median(), 2)),
    positive_pct=("vrp_vol_spread", lambda s: round(100 * (s > 0).mean(), 1)),
    n_obs=("vrp_vol_spread", "size"))
t2"""))

C.append(code("""x = np.arange(len(ROOTS)); w = 0.38
lab = [f"{r}\\n({ROOT_NAMES[r]})" for r in ROOTS]
fig, ax = plt.subplots(figsize=(8, 3.6))
ax.bar(x - w/2, t1.median_iv, w, label="Implied (Black-76 ATM)", color="#3b6ea5")
ax.bar(x + w/2, t1.median_rv, w, label="Forward realized", color="#c8873a")
ax.set_xticks(x, lab); ax.set_ylabel("Annualized volatility, %")
ax.set_title("Median Implied vs Forward Realized Volatility by FX Root, 2010-2026 (6N from 2014)")
ax.legend(frameon=False); plt.show()"""))

C.append(md("""JPY carries the widest gap (0.87 vol points at the median);
NZD is the one root where realized exceeds implied. The premium is slightly
stronger at the short end across tenors."""))

C.append(md("""## 4. Yearly regimes"""))

C.append(code("""daily["year"] = daily.date.dt.year
t4 = (daily.pivot_table(index="year", columns="economic_root",
                        values="vrp_vol_spread", aggfunc="median") * 100).round(2)
vmax = np.nanmax(np.abs(t4.values))
fig, ax = plt.subplots(figsize=(8, 4.6))
im = ax.imshow(t4.values, aspect="auto", cmap="RdBu_r", vmin=-vmax, vmax=vmax)
ax.set_xticks(range(len(t4.columns)), t4.columns)
ax.set_yticks(range(len(t4)), t4.index)
fig.colorbar(im, ax=ax, label="Median IV-RV spread, vol points")
ax.set_title("Yearly Median VRP by Root (2022: negative for all seven roots)")
plt.show()
t4.loc[[2015, 2020, 2022, 2025]]"""))

C.append(md("""## 5. Strategy payoff proxies (step 12)

Twelve variants in three families. The conditioning signal is a leak-free
implied-volatility z-score: per root-tenor, the rolling mean and standard
deviation of the trailing 252 observations ending at t-1 (series shifted one
day before the rolling statistics), minimum 126 observations."""))

C.append(code("""d = daily.sort_values(["economic_root", "target_tenor", "date"]).copy()
g = d.groupby(["economic_root", "target_tenor"], group_keys=False)
d["iv_z"] = (d.black76_iv - g.black76_iv.apply(
    lambda s: s.shift(1).rolling(252, min_periods=126).mean())) / \\
    g.black76_iv.apply(lambda s: s.shift(1).rolling(252, min_periods=126).std())

def daily_series(sel, name):
    s = sel.groupby("date")["vrp_vol_spread"].mean().rename("payoff").reset_index()
    s["strategy"] = name
    return s

MAJORS = ["6E", "6B", "6J", "6S"]
series = [daily_series(d, "static_all_roots_all_tenors")]
for t in (30, 60, 90):
    series.append(daily_series(d[d.target_tenor == t], f"static_{t}d"))
series.append(daily_series(d[d.economic_root != "6N"], "static_ex_6N"))
series.append(daily_series(d[d.economic_root.isin(MAJORS)], "static_major_roots_only"))
dz = d[d.iv_z.notna()]
for thr, tag in ((0.0, "ge_0"), (0.5, "ge_0p5"), (1.0, "ge_1")):
    series.append(daily_series(dz[dz.iv_z >= thr], f"signal_iv_zscore_{tag}"))
for n in (1, 2, 3):
    top = (dz.sort_values("iv_z", ascending=False)
             .groupby(["date", "target_tenor"], group_keys=False).head(n))
    series.append(daily_series(top, f"xs_top{n}_iv_z_by_date_tenor"))
allp = pd.concat(series, ignore_index=True)
allp["payoff_volpts"] = allp.payoff * 100
print(f"strategies: {allp.strategy.nunique()},  strategy-days: {len(allp):,}")"""))

C.append(md("""## 6. Robust inference (step 13)

Forward RV windows overlap across consecutive dates, so naive t-statistics
are badly inflated. Two treatments: Newey-West HAC t-statistics at lags
5/21/63 (63 = one quarter, matching the longest RV horizon, is the headline),
and non-overlapping sampling (every 21st observation at all 21 offsets,
simple t per offset, averaged)."""))

C.append(code("""def nw_t(y, lag):
    res = sm.OLS(np.asarray(y, float), np.ones((len(y), 1))).fit(
        cov_type="HAC", cov_kwds={"maxlags": lag})
    return float(res.tvalues[0])

def nonoverlap_t(y, step=21):
    y = np.asarray(y, float)
    ts = [s.mean() / (s.std(ddof=1) / np.sqrt(len(s)))
          for off in range(step)
          for s in [y[off::step]] if len(s) > 10 and s.std(ddof=1) > 0]
    return float(np.mean(ts))

rows = []
for strat, gg in allp.groupby("strategy"):
    y = gg.sort_values("date").payoff_volpts.to_numpy()
    rows.append({"strategy": strat, "n_days": len(y), "mean": y.mean(),
                 "median": np.median(y), "positive_pct": 100 * (y > 0).mean(),
                 "skew": pd.Series(y).skew(), "ex_kurt": pd.Series(y).kurt(),
                 "t_nw5": nw_t(y, 5), "t_nw63": nw_t(y, 63),
                 "t_nonoverlap21": nonoverlap_t(y)})
ORDER = ["static_all_roots_all_tenors", "static_30d", "static_60d", "static_90d",
         "static_ex_6N", "static_major_roots_only", "signal_iv_zscore_ge_0",
         "signal_iv_zscore_ge_0p5", "signal_iv_zscore_ge_1",
         "xs_top1_iv_z_by_date_tenor", "xs_top2_iv_z_by_date_tenor",
         "xs_top3_iv_z_by_date_tenor"]
t3 = pd.DataFrame(rows).set_index("strategy").loc[ORDER].round(3)
t3"""))

C.append(md("""Reading the table: the static premium is positive but marginal
(NW63 t = 1.79); cross-sectional top-1 high-IV selection nearly doubles the
mean (0.51 vs 0.28 vol points, NW63 t = 2.41) with monotone attenuation
through top-2 and top-3; the time-series threshold family adds little once the
z-score is leak-free. Skewness is negative in every variant: the premium is
compensation for a left tail, realized broadly in 2022. The headline
conditional rule is the best of twelve variants, so its significance should be
discounted for specification search."""))

C.append(code("""fig, ax = plt.subplots(figsize=(8, 3.8))
for s, c, l in [("static_all_roots_all_tenors", "#3b6ea5", "Static, all roots and tenors"),
                ("signal_iv_zscore_ge_0p5", "#2ca02c", "Time-series signal, z >= 0.5"),
                ("xs_top1_iv_z_by_date_tenor", "#d62728", "Cross-sectional top-1 IV z")]:
    gg = allp[allp.strategy == s].sort_values("date")
    ax.plot(gg.date, gg.payoff_volpts.cumsum(), color=c, lw=1.1, label=l)
ax.axhline(0, color="k", lw=0.8)
ax.set_ylabel("Cumulative payoff proxy (vol points)")
ax.set_title("Cumulative Payoff Proxy: Static vs High-IV Conditioning")
ax.legend(frameon=False, fontsize=8)
fig.text(0.01, -0.02, "Payoff proxy: ex-post IV minus forward RV of selected positions. "
         "Excludes transaction costs, hedging, and margin.", fontsize=7, style="italic")
plt.show()"""))

C.append(md("""## 7. Consistency check against the pipeline outputs

The notebook recomputation must match the step 12/13 CSV outputs exactly."""))

C.append(code("""ref = pd.read_csv(os.path.join(VD, "robust_stats_step13",
                                "robust_strategy_summary_v3.csv"), index_col=0)
chk = t3.join(ref[["mean", "t_nw63"]], rsuffix="_ref")
chk["mean_match"] = np.isclose(chk["mean"], chk["mean_ref"], atol=5e-4)
chk["t_match"] = np.isclose(chk["t_nw63"], chk["t_nw63_ref"], atol=5e-3)
assert chk.mean_match.all() and chk.t_match.all(), "MISMATCH vs pipeline outputs"
print("All 12 strategies match the pipeline outputs (mean and NW63 t).")
chk[["mean", "mean_ref", "t_nw63", "t_nw63_ref"]]"""))

nb.cells = C
nb.metadata.kernelspec = {"name": "python3", "display_name": "Python 3",
                          "language": "python"}

out_path = os.path.join(OUT, "vrp_analysis.ipynb")
with open(out_path, "w") as f:
    nbf.write(nb, f)
print("built", out_path)

client = NotebookClient(nb, timeout=600, kernel_name="python3",
                        resources={"metadata": {"path": OUT}})
client.execute()
with open(out_path, "w") as f:
    nbf.write(nb, f)
print("executed and saved", out_path)
