#!/usr/bin/env python3
"""Step 8b: forward realized vol + VRP per option row.
Window: (t, t+H] calendar days on the option's own future_symbol series.
realized_var = 252/n * sum(r2)  (trading-day annualization; sum_r2, n_returns,
span_days stored so alternative conventions can be recomputed).
rv_status: ok | short_span | few_obs | no_data  (no silent drops).
vrp_var = black76_iv^2 - realized_var ; vrp_vol_spread = iv - rv.
"""
import os
import numpy as np
import pandas as pd

WORK = os.environ.get("FX_VRP_WORK", os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
VD = os.path.join(WORK, "clean_v3", "vrp_v3")
PANEL = os.path.join(WORK, "clean_v3", "iv_v3", "research_panel",
                     "research_iv_panel_v3.parquet")
OUT = os.path.join(VD, "vrp_panel_v3.parquet")
DIAG = os.path.join(WORK, "diagnostics")

df = pd.read_parquet(PANEL)
r = pd.read_parquet(os.path.join(VD, "futures_returns.parquet"))
r = r.sort_values(["future_symbol", "date"], kind="stable")

sum_r2 = np.full(len(df), np.nan)
n_ret = np.zeros(len(df), dtype=np.int32)
last_obs = np.full(len(df), np.datetime64("NaT"), dtype="datetime64[ns]")

t_arr = df["date"].to_numpy("datetime64[ns]")
H_arr = df["target_tenor"].to_numpy(np.int64)
end_arr = t_arr + H_arr * np.timedelta64(86400 * 10**9, "ns")

for sym, idx in df.groupby("future_symbol").indices.items():
    g = r[r.future_symbol == sym]
    if not len(g):
        continue
    dts = g["date"].to_numpy("datetime64[ns]")
    c = np.concatenate([[0.0], np.cumsum(g["r2"].to_numpy())])
    i = np.searchsorted(dts, t_arr[idx], side="right")
    j = np.searchsorted(dts, end_arr[idx], side="right")
    sum_r2[idx] = c[j] - c[i]
    n_ret[idx] = j - i
    nz = j > i
    last_obs[idx[nz]] = dts[j[nz] - 1]

span = ((last_obs - t_arr) / np.timedelta64(1, "D"))
span = np.where(n_ret > 0, span, 0.0)

min_n = np.maximum(5, np.floor(0.5 * H_arr * 5 / 7)).astype(int)
status = np.full(len(df), "ok", dtype=object)
status[(n_ret > 0) & (span < 0.6 * H_arr)] = "short_span"
status[(n_ret > 0) & (n_ret < min_n) & (span >= 0.6 * H_arr)] = "few_obs"
status[n_ret == 0] = "no_data"

ok = status == "ok"
rv = np.sqrt(np.where(n_ret > 0, 252.0 * sum_r2 / np.maximum(n_ret, 1), np.nan))
df["rv_sum_r2"] = sum_r2
df["rv_n_returns"] = n_ret
df["rv_span_days"] = span
df["rv_status"] = status
df["realized_vol"] = np.where(ok, rv, np.nan)
df["realized_var"] = df["realized_vol"] ** 2
df["implied_var"] = df["black76_iv"] ** 2
df["vrp_var"] = df["implied_var"] - df["realized_var"]
df["vrp_vol_spread"] = df["black76_iv"] - df["realized_vol"]
df.to_parquet(OUT, index=False)

print(f"rows = {len(df):,}")
print("rv_status:", pd.Series(status).value_counts().to_dict())
print(f"rv ok pct = {100*ok.mean():.2f}%")
okd = df[ok]
print("\n=== median (%) by root: IV | RV | vol spread ===")
m = okd.groupby("economic_root")[["black76_iv", "realized_vol",
                                  "vrp_vol_spread"]].median() * 100
print(m.round(3).to_string())
print("\n=== median vol spread (%) by root x tenor ===")
p = okd.pivot_table(index="economic_root", columns="target_tenor",
                    values="vrp_vol_spread", aggfunc="median") * 100
print(p.round(3).to_string())
print("\n=== mean vrp_var (x1e4) by root ===")
print((okd.groupby("economic_root")["vrp_var"].mean() * 1e4).round(3).to_string())
print(f"\npct rows with positive vol spread = "
      f"{100*(okd.vrp_vol_spread>0).mean():.1f}%")
m.to_csv(os.path.join(DIAG, "vrp_median_by_root.csv"))
p.to_csv(os.path.join(DIAG, "vrp_spread_by_root_tenor.csv"))
okd.assign(year=okd.date.dt.year).groupby(["year"])["vrp_vol_spread"].agg(
    ["median", "mean", "count"]).to_csv(os.path.join(DIAG, "vrp_by_year.csv"))
