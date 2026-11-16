import numpy as np
import pytest
import statsmodels.api as sm

from fxvrp.stats import nw_t, nonoverlap_t


def test_nw_t_matches_statsmodels():
    y = np.random.default_rng(0).normal(0.3, 1.0, 300)
    for lag in (5, 21, 63):
        res = sm.OLS(y, np.ones((len(y), 1))).fit(
            cov_type="HAC", cov_kwds={"maxlags": lag})
        assert nw_t(y, lag) == pytest.approx(res.tvalues[0])


def test_nonoverlap_t_hand_checked():
    # y = 1..24 with step 2: offset 0 holds 1,3,..,23 and offset 1 holds 2,4,..,24.
    # Each has 12 values with sample variance 52, so the standard error is
    # sqrt(52/12); the means are 12 and 13, so the mean t is 12.5 / sqrt(13/3).
    t, k = nonoverlap_t(np.arange(1, 25), step=2)
    assert k == 2
    assert t == pytest.approx(12.5 / np.sqrt(13 / 3))
