"""Step 15: walk-forward forecasts of forward realised volatility.

Target: log(realized_vol) of the step-11 daily cell (date, root, tenor), the
forward RV over (t, t+H] of the option's own underlying futures contract.
Design is fixed in docs/ML_PREREG.md; this module implements it as written.

Features, all known at the close of t:
  har_d/har_w/har_m  log trailing RV over the latest 1/5/22 returns <= t of the
                     option's own future_symbol (age guards 5/14/45 calendar
                     days), built per option row, cell-averaged as in step 11
  log_iv             log Black-76 ATM IV of the cell
  iv_slope           IV(30d) - IV(90d) of the same root-date (0 + flag if absent)
  iv_z               step-12 trailing IV z-score (window ends t-1)
  root, tenor        one-hot identifiers (XGB, LSTM)

Models: IV (log_iv as the forecast), HAR and HAR-IV (OLS per tenor, pooled
across roots), XGB and a 1-layer LSTM (pooled across roots and tenors), plus
two references: SHUF (XGB on a permuted training target, leakage control) and
TRAINMEAN (per-tenor training mean of y).

Walk-forward: expanding window, refit every 63 trading days from the first
trading day >= 2013-01-01. Training rows are purged unless t + H < refit date;
the XGB/LSTM validation slice (last 15% of training dates) gets the same
embargo against the fit rows. Feature scaling uses fit-row statistics only.

Outputs: clean_v3/vrp_v3/ml_step15/
  rv_forecasts_v3.parquet   per-cell OOS forecasts (stays outside the repo)
  forecast_metrics.csv      RMSE, QLIKE, Mincer-Zarnowitz by pooled/tenor/cell
  dm_tests.csv              Diebold-Mariano vs IV and vs HAR
  refit_log.csv             per-refit sample sizes and stopping points
  ml_1_forecast_loss.png
"""
import os
import time
import numpy as np
import pandas as pd
from scipy import stats

from fxvrp.config import vrp_dir, out_dir
from fxvrp.signals import iv_zscore
from fxvrp.stats import nw_t

SEED = 15
FIRST_TEST = "2013-01-01"
REFIT_EVERY = 63
MIN_TRAIN = 2000
VAL_FRAC = 0.15
SEQ_LEN = 22
VAR_FLOOR = 1e-6
ROOTS = ["6A", "6B", "6C", "6E", "6J", "6N", "6S"]
TENORS = [30, 60, 90]
H_TRADING = {30: 21, 60: 41, 90: 62}
SEQ_FEATS = ["har_d", "har_w", "har_m", "log_iv", "iv_slope",
             "iv_slope_missing", "iv_z"]
ID_FEATS = [f"root_{r}" for r in ROOTS] + [f"tenor_{t}" for t in TENORS]
XGB_FEATS = SEQ_FEATS + ID_FEATS
MODELS = ["IV", "HAR", "HAR_IV", "XGB", "LSTM"]
REFS = ["SHUF", "TRAINMEAN"]
HAR_WINDOWS = {"har_d": (1, 5), "har_w": (5, 14), "har_m": (22, 45)}


def trailing_vols(opt, ret):
    """Option-level trailing RV (annualised vol) over the latest n returns
    dated <= t on the option's own future_symbol, with an age guard."""
    out = {k: np.full(len(opt), np.nan) for k in HAR_WINDOWS}
    t_arr = opt["date"].to_numpy("datetime64[ns]")
    day = np.timedelta64(86400 * 10**9, "ns")
    for sym, idx in opt.groupby("future_symbol").indices.items():
        g = ret[ret.future_symbol == sym]
        if not len(g):
            continue
        dts = g["date"].to_numpy("datetime64[ns]")
        c = np.concatenate([[0.0], np.cumsum(g["r2"].to_numpy())])
        k = np.searchsorted(dts, t_arr[idx], side="right")
        for name, (n, max_age) in HAR_WINDOWS.items():
            okn = k >= n
            first = np.where(okn, k - n, 0)
            fresh = okn & (dts[first] >= t_arr[idx] - max_age * day)
            var = 252.0 * (c[k] - c[first]) / n
            vol = np.sqrt(np.maximum(var, VAR_FLOOR))
            out[name][idx] = np.where(fresh, vol, np.nan)
    return out


def build_cells():
    VD = vrp_dir()
    v = pd.read_parquet(os.path.join(VD, "vrp_panel_v3.parquet"))
    ok = v[v.rv_status == "ok"].copy()
    ok = ok[~((ok.economic_root == "6N") & (ok.date < "2014-01-01"))]
    r = pd.read_parquet(os.path.join(VD, "futures_returns.parquet"))
    r = r.sort_values(["future_symbol", "date"], kind="stable")
    for name, arr in trailing_vols(ok, r).items():
        ok[name] = arr

    cells = (ok.groupby(["date", "economic_root", "target_tenor"],
                        as_index=False)
               .agg(black76_iv=("black76_iv", "mean"),
                    realized_vol=("realized_vol", "mean"),
                    vrp_vol_spread=("vrp_vol_spread", "mean"),
                    **{k: (k, "mean") for k in HAR_WINDOWS}))
    cells = cells.sort_values(["economic_root", "target_tenor", "date"],
                              kind="stable").reset_index(drop=True)

    daily = pd.read_parquet(os.path.join(VD, "daily_panel_step11",
                                         "daily_vrp_panel_v3.parquet"))
    key = ["economic_root", "target_tenor", "date"]
    chk = cells[key + ["black76_iv", "realized_vol", "vrp_vol_spread"]]
    pd.testing.assert_frame_equal(
        chk.reset_index(drop=True),
        daily[chk.columns].sort_values(key, kind="stable")
                          .reset_index(drop=True), check_exact=True)

    for k in HAR_WINDOWS:
        cells[k] = np.log(cells[k])
    cells["y"] = np.log(cells["realized_vol"])
    cells["log_iv"] = np.log(cells["black76_iv"])
    cells["iv_z"] = iv_zscore(cells).to_numpy()
    piv = cells.pivot_table(index=["date", "economic_root"],
                            columns="target_tenor", values="black76_iv")
    slope = (piv[30] - piv[90]).rename("iv_slope").reset_index()
    cells = cells.merge(slope, on=["date", "economic_root"], how="left")
    cells["iv_slope_missing"] = cells["iv_slope"].isna().astype(float)
    cells["iv_slope"] = cells["iv_slope"].fillna(0.0)
    for rt in ROOTS:
        cells[f"root_{rt}"] = (cells.economic_root == rt).astype(float)
    for tn in TENORS:
        cells[f"tenor_{tn}"] = (cells.target_tenor == tn).astype(float)
    cells = cells.sort_values(key, kind="stable").reset_index(drop=True)
    return cells, np.sort(daily.date.unique())


def seq_index(s):
    """Row positions of the last SEQ_LEN cells of the same (root, tenor)
    series up to and including each row; -1 = left padding."""
    idx = np.full((len(s), SEQ_LEN), -1, dtype=np.int64)
    for _, pos in s.groupby(["economic_root", "target_tenor"]).indices.items():
        pos = np.sort(pos)
        for lag in range(SEQ_LEN):
            idx[pos[lag:], SEQ_LEN - 1 - lag] = pos[:len(pos) - lag]
    return idx


def fit_ols(X, y):
    X1 = np.column_stack([np.ones(len(X)), X])
    beta, *_ = np.linalg.lstsq(X1, y, rcond=None)
    return beta


def predict_ols(beta, X):
    return beta[0] + X @ beta[1:]


def fit_predict_xgb(Xf, yf, Xv, yv, Xt):
    import xgboost as xgb
    m = xgb.XGBRegressor(objective="reg:squarederror", tree_method="hist",
                         max_depth=4, learning_rate=0.03, subsample=0.8,
                         colsample_bytree=0.8, min_child_weight=20,
                         reg_lambda=1.0, n_estimators=2000,
                         early_stopping_rounds=100, random_state=SEED,
                         n_jobs=4)
    m.fit(Xf, yf, eval_set=[(Xv, yv)], verbose=False)
    return m.predict(Xt), int(m.best_iteration)


def fit_predict_lstm(seq, ids, y, fit, val, test):
    import torch
    from torch import nn
    torch.manual_seed(SEED)
    torch.use_deterministic_algorithms(True)

    class Net(nn.Module):
        def __init__(self):
            super().__init__()
            self.lstm = nn.LSTM(len(SEQ_FEATS), 16, num_layers=1,
                                batch_first=True)
            self.head = nn.Linear(16 + len(ID_FEATS), 1)

        def forward(self, xs, xi):
            _, (h, _) = self.lstm(xs)
            return self.head(torch.cat([h[-1], xi], dim=1)).squeeze(1)

    mu, sd = y[fit].mean(), y[fit].std()
    T = lambda a: torch.as_tensor(a, dtype=torch.float32)
    xs_f, xi_f, y_f = T(seq[fit]), T(ids[fit]), T((y[fit] - mu) / sd)
    xs_v, xi_v, y_v = T(seq[val]), T(ids[val]), T((y[val] - mu) / sd)
    net = Net()
    opt = torch.optim.Adam(net.parameters(), lr=1e-3)
    gen = torch.Generator().manual_seed(SEED)
    best, best_state, best_ep, bad = np.inf, None, 0, 0
    for ep in range(100):
        net.train()
        perm = torch.randperm(len(y_f), generator=gen)
        for b in range(0, len(perm), 512):
            j = perm[b:b + 512]
            opt.zero_grad()
            loss = ((net(xs_f[j], xi_f[j]) - y_f[j]) ** 2).mean()
            loss.backward()
            opt.step()
        net.eval()
        with torch.no_grad():
            vl = float(((net(xs_v, xi_v) - y_v) ** 2).mean())
        if vl < best - 1e-6:
            best, best_ep, bad = vl, ep + 1, 0
            best_state = {k: t.clone() for k, t in net.state_dict().items()}
        else:
            bad += 1
            if bad >= 8:
                break
    net.load_state_dict(best_state)
    net.eval()
    with torch.no_grad():
        p = net(T(seq[test]), T(ids[test])).numpy()
    return p * sd + mu, best_ep


def walk_forward(s, dates):
    import torch
    torch.set_num_threads(4)
    first = dates[dates >= np.datetime64(FIRST_TEST)]
    refits = list(first[::REFIT_EVERY])
    d = s["date"].to_numpy("datetime64[ns]")
    end = d + s["target_tenor"].to_numpy() * np.timedelta64(1, "D")
    tenor = s["target_tenor"].to_numpy()
    y = s["y"].to_numpy()
    sidx = seq_index(s)
    har = ["har_d", "har_w", "har_m"]
    cont = [c for c in SEQ_FEATS if c != "iv_slope_missing"]

    while (end < refits[0]).sum() < MIN_TRAIN:
        print(f"training window too thin at {str(refits[0])[:10]}, moving on")
        refits.pop(0)
    print(f"first test date: {str(refits[0])[:10]}, refits: {len(refits)}")

    pred = {m: np.full(len(s), np.nan) for m in MODELS + REFS}
    refit_col = np.full(len(s), np.datetime64("NaT"), dtype="datetime64[ns]")
    log = []
    for k, T0 in enumerate(refits):
        t_start = time.time()
        T1 = refits[k + 1] if k + 1 < len(refits) else np.datetime64("2100-01-01")
        train = end < T0
        test = (d >= T0) & (d < T1)
        if not test.any():
            continue
        val_start = np.quantile(d[train].astype("int64"), 1 - VAL_FRAC)
        val_start = np.datetime64(int(val_start), "ns")
        val = train & (d >= val_start)
        fit = train & (end < val_start)
        refit_col[test] = T0

        pred["IV"][test] = s.loc[test, "log_iv"].to_numpy()
        for tn in TENORS:
            tr, te = train & (tenor == tn), test & (tenor == tn)
            if not te.any():
                continue
            pred["TRAINMEAN"][te] = y[tr].mean()
            b = fit_ols(s.loc[tr, har].to_numpy(), y[tr])
            pred["HAR"][te] = predict_ols(b, s.loc[te, har].to_numpy())
            cols = har + ["log_iv"]
            b = fit_ols(s.loc[tr, cols].to_numpy(), y[tr])
            pred["HAR_IV"][te] = predict_ols(b, s.loc[te, cols].to_numpy())

        X = s[XGB_FEATS].to_numpy(float).copy()
        ci = [XGB_FEATS.index(c) for c in cont]
        mu, sd = X[fit][:, ci].mean(0), X[fit][:, ci].std(0)
        X[:, ci] = (X[:, ci] - mu) / sd
        p, it_x = fit_predict_xgb(X[fit], y[fit], X[val], y[val], X[test])
        pred["XGB"][test] = p

        rng = np.random.default_rng(SEED + k)
        y_sh = y.copy()
        tr_pos = np.flatnonzero(train)
        y_sh[tr_pos] = y[rng.permutation(tr_pos)]
        p, it_s = fit_predict_xgb(X[fit], y_sh[fit], X[val], y_sh[val],
                                  X[test])
        pred["SHUF"][test] = p

        Xs = X[:, [XGB_FEATS.index(c) for c in SEQ_FEATS]]
        Xs = np.vstack([Xs, np.zeros((1, Xs.shape[1]))])
        seq = Xs[sidx]  # -1 indexes the zero padding row
        ids = s[ID_FEATS].to_numpy(float)
        p, ep = fit_predict_lstm(seq, ids, y, fit, val, test)
        pred["LSTM"][test] = p

        log.append({"refit_date": str(T0)[:10], "n_train": int(train.sum()),
                    "n_fit": int(fit.sum()), "n_val": int(val.sum()),
                    "n_test": int(test.sum()),
                    "train_last_target_end": str(end[train].max())[:10],
                    "xgb_best_iter": it_x, "shuf_best_iter": it_s,
                    "lstm_best_epoch": ep,
                    "seconds": round(time.time() - t_start, 1)})
        print(f"refit {k + 1:2d}/{len(refits)} {str(T0)[:10]} "
              f"train {train.sum():6d} test {test.sum():5d} "
              f"xgb {it_x:4d} lstm {ep:3d} ({log[-1]['seconds']}s)",
              flush=True)

    out = s[["date", "economic_root", "target_tenor", "y", "realized_vol",
             "black76_iv", "vrp_vol_spread", "iv_z"]].copy()
    out["refit_date"] = refit_col
    for m in MODELS + REFS:
        out[f"pred_{m}"] = pred[m]
    out = out[out.refit_date.notna()].reset_index(drop=True)
    return out, pd.DataFrame(log)


def qlike(y, p):
    ratio = np.exp(2 * y) / np.exp(2 * p)
    return ratio - np.log(ratio) - 1


def metrics(f):
    rows = []
    groups = [("pooled", "all", "all", f)]
    groups += [("tenor", "all", tn, g) for tn, g in f.groupby("target_tenor")]
    groups += [("root_tenor", rt, tn, g)
               for (rt, tn), g in f.groupby(["economic_root", "target_tenor"])]
    for level, rt, tn, g in groups:
        y = g["y"].to_numpy()
        for m in MODELS + REFS:
            p = g[f"pred_{m}"].to_numpy()
            b, a = np.polyfit(p, y, 1)
            r2 = np.corrcoef(p, y)[0, 1] ** 2
            rows.append({"level": level, "root": rt, "tenor": tn, "model": m,
                         "n": len(y),
                         "rmse": np.sqrt(np.mean((y - p) ** 2)),
                         "qlike": qlike(y, p).mean(),
                         "mz_a": a, "mz_b": b, "mz_r2": r2})
    return pd.DataFrame(rows)


def dm_tests(f):
    rows = []
    groups = [("pooled", "all", "all", f, 62)]
    groups += [("tenor", "all", tn, g, H_TRADING[tn])
               for tn, g in f.groupby("target_tenor")]
    groups += [("root_tenor", rt, tn, g, H_TRADING[tn])
               for (rt, tn), g in f.groupby(["economic_root",
                                             "target_tenor"])]
    losses = {"se": lambda y, p: (y - p) ** 2, "qlike": qlike}
    for level, rt, tn, g, lag in groups:
        g = g.sort_values("date")
        y = g["y"].to_numpy()
        for bench in ("IV", "HAR", "TRAINMEAN"):
            cands = MODELS + REFS if bench != "TRAINMEAN" else ["SHUF"]
            for m in cands:
                if m == bench:
                    continue
                for lname, lf in losses.items():
                    dl = (lf(y, g[f"pred_{m}"].to_numpy())
                          - lf(y, g[f"pred_{bench}"].to_numpy()))
                    dd = pd.Series(dl).groupby(g["date"].to_numpy()).mean()
                    t = nw_t(dd.to_numpy(), lag)
                    rows.append({"level": level, "root": rt, "tenor": tn,
                                 "model": m, "benchmark": bench,
                                 "loss": lname, "n_dates": len(dd),
                                 "mean_loss_diff": dd.mean(), "dm_stat": t,
                                 "p_two_sided": 2 * stats.norm.sf(abs(t)),
                                 "p_one_sided_better": stats.norm.cdf(t)})
    return pd.DataFrame(rows)


def chart(met, OUTD):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"figure.dpi": 200, "savefig.dpi": 200,
                         "font.size": 9, "axes.grid": True,
                         "grid.alpha": 0.3, "axes.axisbelow": True})
    t = met[met.level == "tenor"]
    fig, axes = plt.subplots(1, 2, figsize=(8.0, 3.4))
    models = MODELS + ["SHUF"]
    cols = ["#7f7f7f", "#1f77b4", "#2ca02c", "#d62728", "#9467bd", "#bcbd22"]
    x = np.arange(len(TENORS)); w = 0.13
    for ax, metric, lab in ((axes[0], "rmse", "RMSE, log RV"),
                            (axes[1], "qlike", "QLIKE")):
        for i, m in enumerate(models):
            v = t[t.model == m].set_index("tenor").loc[TENORS, metric]
            ax.bar(x + (i - 2.5) * w, v, w, label=m, color=cols[i])
        ax.set_xticks(x, [f"{tn}d" for tn in TENORS])
        ax.set_title(lab)
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, fontsize=7, ncol=len(models), loc="lower center")
    fig.suptitle("Out-of-sample forward RV forecast loss by tenor, "
                 "walk-forward 2013-2026", fontsize=10)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(os.path.join(OUTD, "ml_1_forecast_loss.png"))
    plt.close(fig)


def run():
    OUTD = out_dir("ml_step15")
    np.random.seed(SEED)
    cells, dates = build_cells()
    need = ["har_d", "har_w", "har_m", "iv_z"]
    s = cells.dropna(subset=need).reset_index(drop=True)
    print(f"cells: {len(cells):,}  modelling sample: {len(s):,}")
    print("feature coverage (non-missing share):")
    print(cells[need].notna().mean().round(4).to_string())
    print(f"iv_slope missing share: {cells.iv_slope_missing.mean():.4f}")

    f, log = walk_forward(s, dates)
    f.to_parquet(os.path.join(OUTD, "rv_forecasts_v3.parquet"), index=False)
    log.to_csv(os.path.join(OUTD, "refit_log.csv"), index=False)

    met = metrics(f)
    met.round(6).to_csv(os.path.join(OUTD, "forecast_metrics.csv"),
                        index=False)
    dm = dm_tests(f)
    dm.round(6).to_csv(os.path.join(OUTD, "dm_tests.csv"), index=False)
    chart(met, OUTD)

    print(f"\nOOS cells: {len(f):,}, dates {f.date.min().date()} .. "
          f"{f.date.max().date()}")
    print("\n=== pooled / by tenor ===")
    print(met[met.level != "root_tenor"]
          .pivot_table(index=["tenor", "model"],
                       values=["rmse", "qlike", "mz_r2"], sort=False)
          .round(4).to_string())
    print("\n=== DM (pooled + tenor) ===")
    print(dm[dm.level != "root_tenor"]
          .pivot_table(index=["tenor", "model"],
                       columns=["benchmark", "loss"],
                       values="p_two_sided", sort=False)
          .round(4).to_string())
    pooled = met[(met.level == "pooled") & (met.model == "SHUF")].iloc[0]
    dsh = dm[(dm.level == "pooled") & (dm.model == "SHUF")
             & (dm.benchmark == "TRAINMEAN") & (dm.loss == "se")].iloc[0]
    passed = (pooled.mz_r2 <= 0.01) and (dsh.p_one_sided_better > 0.05)
    print(f"\nSHUF control: pooled MZ R2 {pooled.mz_r2:.4f}, one-sided p "
          f"(better than TRAINMEAN) {dsh.p_one_sided_better:.3f} -> "
          f"{'PASS' if passed else 'FAIL'}")

