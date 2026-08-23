#!/usr/bin/env python3
"""Step 6: Black-76 implied vol on the ATM panel. r=0, tau=dte/365.25.
Vectorized bisection (80 iters on [1e-6, 5]). Saves full IV panel."""
import os
import numpy as np
import pandas as pd
from scipy.special import ndtr

WORK = os.environ.get("FX_VRP_WORK", os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
ATM = os.path.join(WORK, "clean_v3", "atm_export_v3", "atm_panel_v3.parquet")
OUTD = os.path.join(WORK, "clean_v3", "iv_v3")
OUT = os.path.join(OUTD, "iv_panel_v3.parquet")
DIAG = os.path.join(WORK, "diagnostics")

def black76(F, K, tau, sigma, cp):
    st = sigma * np.sqrt(tau)
    with np.errstate(divide="ignore", invalid="ignore"):
        d1 = (np.log(F / K) + 0.5 * sigma**2 * tau) / st
    d2 = d1 - st
    return cp * (F * ndtr(cp * d1) - K * ndtr(cp * d2))

def main():
    os.makedirs(OUTD, exist_ok=True)
    df = pd.read_parquet(ATM)
    F = df.future_settle.to_numpy(float)
    K = df.strike_price.to_numpy(float)
    P = df.option_settle.to_numpy(float)
    tau = df.dte.to_numpy(float) / 365.25
    cp = np.where(df.option_type.to_numpy() == "C", 1.0, -1.0)

    intrinsic = np.maximum(cp * (F - K), 0.0)
    lo = np.full(len(df), 1e-6)
    hi = np.full(len(df), 5.0)
    p_hi = black76(F, K, tau, hi, cp)

    below = P < intrinsic - 1e-12
    toohigh = P > p_hi
    solvable = ~(below | toohigh)

    l, h = lo.copy(), hi.copy()
    for _ in range(80):
        mid = 0.5 * (l + h)
        pm = black76(F, K, tau, mid, cp)
        up = pm < P
        l = np.where(up, mid, l)
        h = np.where(up, h, mid)
    sigma = 0.5 * (l + h)
    model = black76(F, K, tau, sigma, cp)
    err = np.abs(model - P)
    rel_err = err / np.maximum(P, 1e-300)

    fitted = solvable & ((rel_err <= 1e-6) | (err <= 1e-10))
    pinned_low = solvable & ~fitted & (sigma <= 2e-6)
    near_intr = solvable & ~fitted & (P - intrinsic <= np.maximum(1e-9, 1e-4 * P))

    status = np.full(len(df), "no_converge", dtype=object)
    status[fitted] = "ok"
    status[near_intr & ~fitted] = "ok_near_intrinsic"
    status[pinned_low & ~fitted & ~near_intr] = "ok_near_intrinsic"
    status[below] = "below_intrinsic"
    status[toohigh] = "above_upper_bound"

    valid = np.isin(status, ["ok", "ok_near_intrinsic"])
    df["black76_iv"] = np.where(valid, sigma, np.nan)
    df["iv_status"] = status
    df["iv_model_abs_err"] = err

    df.to_parquet(OUT, index=False)
    n, nv = len(df), int(valid.sum())
    print(f"input rows     = {n:,}   (target 440,467)")
    print(f"valid IV rows  = {nv:,}   (target 440,462)")
    print(f"valid IV pct   = {100*nv/n:.4f}%   (target 99.9989%)")
    print(f"invalid rows   = {n-nv}   (target 5)")
    print("status counts:", pd.Series(status).value_counts().to_dict())
    med = (df.loc[valid].assign(ivpct=lambda x: 100 * x.black76_iv)
           .groupby("economic_root")["ivpct"].median())
    tgt = {"6A": 9.824358, "6B": 7.969980, "6C": 6.997066, "6E": 7.530707,
           "6J": 9.048753, "6N": 9.690925, "6S": 7.695687}
    print("\nmedian IV%% by root vs target:")
    for r_, v in med.items():
        print(f"  {r_}: {v:.6f}   (target {tgt[r_]:.6f}  diff {v-tgt[r_]:+.6f})")
    cmp = pd.DataFrame({"median_iv_pct": med, "target": pd.Series(tgt)})
    cmp.to_csv(os.path.join(DIAG, "iv_median_by_root_vs_target.csv"))

if __name__ == "__main__":
    main()
