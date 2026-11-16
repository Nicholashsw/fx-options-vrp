import numpy as np
import pytest

from fxvrp.stats import nw_t, nonoverlap_t


def nw_t_by_hand(y, lag):
    # Newey-West with Bartlett weights: var(mean) = (g0 + 2 * sum w_j g_j) / n,
    # with g_j the lag-j autocovariance and w_j = 1 - j / (lag + 1).
    n = len(y)
    e = y - y.mean()
    long_run = e @ e / n
    for j in range(1, lag + 1):
        long_run += 2 * (1 - j / (lag + 1)) * (e[j:] @ e[:-j]) / n
    return y.mean() / np.sqrt(long_run / n)


def test_nw_t_matches_the_formula():
    y = np.random.default_rng(0).normal(0.3, 1.0, 300)
    for lag in (5, 21, 63):
        assert nw_t(y, lag) == pytest.approx(nw_t_by_hand(y, lag))


def test_nonoverlap_t_hand_checked():
    # y = 1..24 with step 2: offset 0 holds 1,3,..,23 and offset 1 holds 2,4,..,24.
    # Each has 12 values with sample variance 52, so the standard error is
    # sqrt(52/12); the means are 12 and 13, so the mean t is 12.5 / sqrt(13/3).
    t, k = nonoverlap_t(np.arange(1, 25), step=2)
    assert k == 2
    assert t == pytest.approx(12.5 / np.sqrt(13 / 3))
