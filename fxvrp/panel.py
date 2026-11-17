"""Step 11: the daily (date, root, tenor) panel from the option-level VRP panel."""
import os
import pandas as pd

from fxvrp.config import vrp_dir, out_dir
from fxvrp.signals import iv_zscore


def data_checks(df, ok, daily):
    """Counts and shares that the README, paper and report quote about the data."""
    n13 = df[(df.economic_root == "6N") & (df.date.dt.year == 2013)]
    hi13 = n13[n13.black76_iv > 0.20]
    cells = (df[df.rv_status == "ok"]
             .groupby(["date", "economic_root", "target_tenor"], as_index=False)
             .agg(iv=("black76_iv", "mean"), oi=("open_interest", "sum")))
    flagged = cells[(cells.iv > 0.20) & (cells.oi == 0)]
    n_post = daily[(daily.economic_root == "6N") & (daily.date >= "2014-01-01")]
    rows = {
        "option_rows_all": len(df),
        "option_rows_rv_ok": len(df[df.rv_status == "ok"]),
        "option_rows_rv_excluded": int((df.rv_status != "ok").sum()),
        "option_rows_ok_after_6N_exclusion": len(ok),
        "option_rows_open_interest_missing_pct": 100 * df.open_interest.isna().mean(),
        "futures_settle_rows": len(pd.read_parquet(os.path.join(vrp_dir(), "futures_settle_daily.parquet"))),
        "futures_return_rows": len(pd.read_parquet(os.path.join(vrp_dir(), "futures_returns.parquet"))),
        "daily_rows": len(daily),
        "daily_date_min": daily.date.min().date(),
        "daily_date_max": daily.date.max().date(),
        "daily_valid_z_pct": 100 * iv_zscore(daily).notna().mean(),
        "tenor_diff_days_mean": ok.tenor_diff.mean(),
        "tenor_diff_days_max": ok.tenor_diff.max(),
        "n6_2013_rows": len(n13),
        "n6_2013_rows_with_open_interest": int(n13.open_interest.notna().sum()),
        "n6_2013_rows_iv_above_20": len(hi13),
        "n6_2013_iv_above_20_median_iv": 100 * hi13.black76_iv.median(),
        "n6_2013_iv_above_20_max_iv": 100 * hi13.black76_iv.max(),
        "n6_2013_iv_above_20_median_rv": 100 * hi13.realized_vol.median(),
        "cells_iv_above_20_no_open_interest": len(flagged),
        "cells_iv_above_20_no_open_interest_6N_2013": int(
            ((flagged.economic_root == "6N") & (flagged.date.dt.year == 2013)).sum()),
        "n6_from_2014_cells_no_open_interest_pct": 100 * (n_post.open_interest == 0).mean(),
    }
    return pd.Series(rows, name="value").rename_axis("metric")


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
    data_checks(df, ok, daily).to_csv(os.path.join(OUTD, "data_checks.csv"))

    print(f"option-level ok rows: {len(ok):,}")
    print(f"daily panel rows:     {len(daily):,}")
    print(f"date range:           {daily.date.min().date()} .. {daily.date.max().date()}")
    print(daily.groupby("target_tenor").size().to_string())
    print(daily.groupby("economic_root").size().to_string())
