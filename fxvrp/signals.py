"""The trailing implied-volatility z-score."""

Z_WINDOW, Z_MIN = 252, 126


def iv_zscore(d):
    """IV z-score per (root, tenor) from the trailing 252 observations before t; d must be sorted by date."""
    # Rolling window over obs t-252..t-1 (shift 1), so nothing at or after t is used.
    g = d.groupby(["economic_root", "target_tenor"], group_keys=False)
    iv_lag_mean = g["black76_iv"].apply(
        lambda s: s.shift(1).rolling(Z_WINDOW, min_periods=Z_MIN).mean())
    iv_lag_std = g["black76_iv"].apply(
        lambda s: s.shift(1).rolling(Z_WINDOW, min_periods=Z_MIN).std())
    return (d["black76_iv"] - iv_lag_mean) / iv_lag_std
