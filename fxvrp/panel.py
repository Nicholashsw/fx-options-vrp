"""Step 11: the daily (date, root, tenor) panel from the option-level VRP panel."""
import os
import pandas as pd

from fxvrp.config import vrp_dir, out_dir


def run():
    # Only rv_status == 'ok' rows enter. Within each (date, economic_root,
    # target_tenor) cell the up-to-6 selected ATM contracts (calls and puts,
    # top 3 by the step-6 rerank) are equal-weight averaged.
    VD = vrp_dir()
    OUTD = out_dir("daily_panel_step11")

    df = pd.read_parquet(os.path.join(VD, "vrp_panel_v3.parquet"))
    ok = df[df.rv_status == "ok"].copy()

    # 6N anomaly: in 2013 legacy 6N options still settle at implied volatility
    # above 20% (median 28.5%) against a median realised volatility of 9.5%.
    # 102 of the 128 daily cells with IV > 20% and no recorded open interest
    # are 6N in 2013; high-IV days for other roots coincide with market stress
    # (2011, Brexit, SNB de-peg, COVID). The cut-off was chosen after comparing
    # implied with realised volatility over the full sample.
    # Rule: 6N enters the sample 2014-01-01.
    n_drop = ((ok.economic_root == "6N") & (ok.date < "2014-01-01")).sum()
    ok = ok[~((ok.economic_root == "6N") & (ok.date < "2014-01-01"))]
    print(f"6N pre-2014 rows dropped: {n_drop:,}")

    daily = (ok.groupby(["date", "economic_root", "target_tenor"], as_index=False)
               .agg(black76_iv=("black76_iv", "mean"),
                    realized_vol=("realized_vol", "mean"),
                    vrp_vol_spread=("vrp_vol_spread", "mean"),
                    vrp_var=("vrp_var", "mean"),
                    n_contracts=("black76_iv", "size"),
                    open_interest=("open_interest", "sum")))
    daily = daily.sort_values(["economic_root", "target_tenor", "date"],
                              kind="stable").reset_index(drop=True)
    out = os.path.join(OUTD, "daily_vrp_panel_v3.parquet")
    daily.to_parquet(out, index=False)

    print(f"option-level ok rows: {len(ok):,}")
    print(f"daily panel rows:     {len(daily):,}")
    print(f"date range:           {daily.date.min().date()} .. {daily.date.max().date()}")
    print(daily.groupby("target_tenor").size().to_string())
    print(daily.groupby("economic_root").size().to_string())
