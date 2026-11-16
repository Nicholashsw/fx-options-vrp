import numpy as np
import pandas as pd

from fxvrp.signals import iv_zscore


def make_panel(n=400):
    rng = np.random.default_rng(1)
    frames = []
    for root in ("6E", "6J"):
        frames.append(pd.DataFrame({
            "economic_root": root, "target_tenor": 30,
            "date": pd.bdate_range("2020-01-01", periods=n),
            "black76_iv": rng.uniform(0.05, 0.15, n)}))
    return pd.concat(frames, ignore_index=True)


def test_z_at_t_ignores_later_values():
    d = make_panel()
    z = iv_zscore(d)
    cut = pd.Timestamp(d.date.iloc[300])
    changed = d.copy()
    later = changed.date > cut
    changed.loc[later, "black76_iv"] *= 10
    z2 = iv_zscore(changed)
    assert z[~later].notna().any()
    pd.testing.assert_series_equal(z[~later], z2[~later])
