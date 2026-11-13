"""The pandas reference (scripts/intraday_rv.py) on the cases q/tests/test_rv.q
checks, so the two engines are held to the same expectations."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import intraday_rv as rv  # noqa: E402

CAL = pd.to_datetime(["2026-07-13", "2026-07-14", "2026-07-15", "2026-07-16", "2026-07-17", "2026-07-20"])
T = pd.Timestamp


def test_daylight_saving():
    assert rv.dst_range(2026) == (T("2026-03-08").date(), T("2026-11-01").date())
    assert rv.dst_range(2017) == (T("2017-03-12").date(), T("2017-11-05").date())


def test_settlement_time():
    got = rv.settle_time(["2026-07-15", "2026-01-15", "2026-03-09", "2026-11-02"])
    want = pd.to_datetime(["2026-07-15 19:00", "2026-01-15 20:00", "2026-03-09 19:00", "2026-11-02 20:00"])
    assert (got == want.to_numpy()).all()


def test_sessions():
    t = pd.to_datetime(["2026-07-15 18:55", "2026-07-15 19:00", "2026-07-15 19:00:00.000000001",
                        "2026-07-17 21:00", "2026-07-19 23:00", "2026-07-20 19:01"], format="ISO8601")
    got = pd.Series(rv.session_of(CAL, t))
    want = pd.Series(pd.to_datetime(["2026-07-15", "2026-07-15", "2026-07-16", "2026-07-20", "2026-07-20", None]))
    pd.testing.assert_series_equal(got, want.astype("datetime64[ns]"), check_names=False)


@pytest.fixture
def path_bars():
    mins = np.arange(151)
    return pd.DataFrame({"sym": "A", "root": "X", "time": T("2026-07-15 17:00") + pd.to_timedelta(mins, "min"),
                         "close": 1.1 + 0.001 * np.sin(0.37 * mins), "volume": 1}), mins


def test_measures_on_a_known_path(path_bars):
    b, mins = path_bars
    m = rv.measures(rv.sample(b, rv.K5), CAL).set_index("session")
    c = b["close"][mins % 5 == 0].to_numpy()
    r = np.diff(np.log(c))
    s15, s16 = r[:24], r[24:]
    assert list(m["n"]) == [24, 6]
    assert m.loc["2026-07-15", "rv"] == pytest.approx((s15 ** 2).sum(), abs=1e-15)
    assert m.loc["2026-07-16", "rv"] == pytest.approx((s16 ** 2).sum(), abs=1e-15)
    assert m.loc["2026-07-15", "bv"] == pytest.approx(np.pi / 2 * (np.abs(s15[1:]) * np.abs(s15[:-1])).sum(), abs=1e-15)
    m1 = rv.measures(rv.sample(b, rv.K1), CAL).set_index("session")
    assert m1.loc["2026-07-15", "n"] == 120


def test_gap_drops_the_return():
    g = pd.DataFrame({"sym": "B", "root": "X", "close": [1.0, 1.01, 1.05], "volume": 1,
                      "time": pd.to_datetime(["2026-07-13 15:00", "2026-07-13 15:05", "2026-07-20 15:00"])})
    assert list(rv.measures(rv.sample(g, rv.K5), CAL)["n"]) == [1]


def test_daily_table(path_bars):
    b, _ = path_bars
    d = rv.daily(b, CAL)
    assert len(d) == 2 and d[["rv5", "rv1", "bv5"]].notna().all().all()
    assert list(d["volume"]) == [121, 30]


def test_running_equals_batch():
    rng = np.random.default_rng(11)
    n = 3000
    b = pd.DataFrame({"sym": rng.choice(["E", "J", "N"], n), "root": "X",
                      "time": T("2026-07-13 12:00") + pd.to_timedelta(np.sort(rng.integers(0, 400_000, n)), "s"),
                      "volume": 1})
    b["close"] = np.exp(b.groupby("sym").cumcount().map(lambda _: 0) + 0.002 * rng.standard_normal(n).cumsum())
    batch = rv.measures(rv.sample(b, rv.K5), CAL)[["sym", "session", "n", "rv", "bv"]]
    run = rv.Running(CAL)
    for s, t, c in zip(b["sym"], b["time"], b["close"]):
        run.on_bar(s, t, c)
    run.flush()
    live = run.table()
    assert list(batch["n"]) == list(live["n"])
    assert (batch["session"].to_numpy() == live["session"].to_numpy()).all()
    np.testing.assert_allclose(batch["rv"], live["rv"], rtol=1e-12)
    np.testing.assert_allclose(batch["bv"], live["bv"], rtol=1e-12)


def test_forward_windows():
    d = pd.DataFrame({"sym": "A", "session": CAL[:5], "rv5": 1e-4 * np.arange(1, 6), "bv5": 1e-4 * np.arange(1, 6),
                      "rv1": 2e-4 * np.arange(1, 6), "n5": 200})
    p = pd.DataFrame({"row_id": [0, 1, 2], "date": pd.to_datetime(["2026-07-13", "2026-07-15", "2026-07-17"]),
                      "sym": "A", "tenor": [3, 7, 3]})
    f = rv.forward(d, p).set_index("row_id")
    assert f.loc[0, "n_sessions"] == 3 and f.loc[0, "rv5_sum"] == pytest.approx(9e-4)
    assert f.loc[1, "n_sessions"] == 2 and f.loc[1, "rv5_sum"] == pytest.approx(9e-4)
    assert f.loc[0, "rvol5"] == pytest.approx(np.sqrt(252 * 3e-4))
    assert f.loc[2, "n_sessions"] == 0 and np.isnan(f.loc[2, "rvol5"])
    f2 = rv.forward(d.assign(n5=[200, 50, 200, 200, 200]), p, min_n5=100).set_index("row_id")
    assert f2.loc[0, "n_sessions"] == 2 and f2.loc[0, "rv5_sum"] == pytest.approx(7e-4)
