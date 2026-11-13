"""Intraday realised measures in pandas: the reference for the q engine in q/.

Every function mirrors one in q/rv.q, with the same conventions:

- a bar's time is its CLOSE (Databento stamps the open; step 15 adds a minute);
- the 5-minute sample is the last close in each bucket, the bucket labelled by
  its end, so a bar closing exactly on a boundary closes that bucket;
- a return belongs to the settlement session in which it ends, and nothing
  resets at a session boundary, so a session's sum runs settlement to settlement;
- a return spanning more than four days is dropped;
- CME FX futures settle at 14:00 Chicago time (19:00 UTC under US daylight
  saving, 20:00 UTC otherwise), and a bar belongs to the first calendar
  settlement at or after its close.

Step 16 uses this module to check the q output and, with --engine python, to
compute the measures without q.
"""

import numpy as np
import pandas as pd

K5 = pd.Timedelta(minutes=5)
K1 = pd.Timedelta(minutes=1)
GAP_MAX = pd.Timedelta(days=4)
ONE_NS = pd.Timedelta(1, "ns")


def _first_sunday(d):
    d = pd.Timestamp(d)
    return d + pd.Timedelta(days=(6 - d.weekday()) % 7)


def dst_range(year):
    """US daylight saving: second Sunday of March to first Sunday of November."""
    return (_first_sunday(f"{year}-03-01") + pd.Timedelta(days=7)).date(), _first_sunday(f"{year}-11-01").date()


def settle_time(dates):
    """Settlement timestamps (UTC, naive) for an array of dates."""
    d = pd.to_datetime(pd.Series(dates)).dt.normalize()
    years = d.dt.year.unique()
    ranges = {y: dst_range(y) for y in years}
    start = pd.to_datetime(d.dt.year.map(lambda y: ranges[y][0]))
    end = pd.to_datetime(d.dt.year.map(lambda y: ranges[y][1]))
    summer = (d >= start) & (d < end)
    return (d + pd.to_timedelta(np.where(summer, 19, 20), unit="h")).to_numpy()


def session_of(cal, times):
    """First calendar date whose settlement is at or after each time; NaT past the end."""
    cal = np.sort(pd.to_datetime(pd.Series(cal)).dt.normalize().unique())
    st = settle_time(cal)
    idx = np.searchsorted(st, pd.to_datetime(pd.Series(times)).to_numpy(), side="left")
    out = np.full(len(idx), np.datetime64("NaT", "ns"))
    ok = idx < len(cal)
    out[ok] = cal[idx[ok]]
    return out


def sample(bars, k):
    """Last close and summed volume per contract and k bucket (labelled by its end)."""
    b = bars.assign(bucket=(bars["time"] - ONE_NS).dt.floor(k) + k)
    s = (b.sort_values(["sym", "time"], kind="stable")
          .groupby(["sym", "bucket"], sort=True)
          .agg(close=("close", "last"), volume=("volume", "sum"))
          .reset_index()
          .rename(columns={"bucket": "time"}))
    return s


def returns(s):
    s = s.sort_values(["sym", "time"], kind="stable").copy()
    g = s.groupby("sym", sort=False)
    gap = s["time"] - g["time"].shift(1)
    r = np.log(s["close"]) - np.log(g["close"].shift(1))
    s["r"] = r.where(gap <= GAP_MAX)
    return s


def measures(s, cal):
    s = returns(s)
    s["session"] = session_of(cal, s["time"])
    s = s[s["r"].notna() & s["session"].notna()].copy()
    s["prev_abs"] = s.groupby(["sym", "session"])["r"].shift(1).abs()
    s["bp"] = s["r"].abs() * s["prev_abs"]
    m = s.groupby(["sym", "session"]).agg(n=("r", "size"), rv=("r", lambda x: float((x * x).sum())),
                                          bv=("bp", "sum"), last_sample=("time", "last")).reset_index()
    m["bv"] *= np.pi / 2
    return m


def daily(bars, cal):
    """The table q/daily_rv.q writes, for the same bars."""
    b = bars.copy()
    b["session"] = session_of(cal, b["time"])
    b = b[b["session"].notna()]
    info = (b.sort_values(["sym", "time"], kind="stable").groupby(["sym", "session"])
             .agg(root=("root", "first"), first_bar=("time", "first"), last_bar=("time", "last"),
                  volume=("volume", "sum")).reset_index())
    m5 = measures(sample(bars, K5), cal).rename(columns={"n": "n5", "rv": "rv5", "bv": "bv5"})
    m1 = measures(sample(bars, K1), cal).rename(columns={"n": "n1", "rv": "rv1"})
    out = (info.merge(m5[["sym", "session", "n5", "rv5", "bv5"]], on=["sym", "session"], how="left")
               .merge(m1[["sym", "session", "n1", "rv1"]], on=["sym", "session"], how="left"))
    return out.sort_values(["sym", "session"]).reset_index(drop=True)


def forward(d, panel, min_n5=0):
    """Sum of daily measures over (t, t+H] of each option's own contract (q: .rv.forward).
    Sessions with fewer than min_n5 five-minute returns are left out."""
    d = d[d["rv5"].notna() & (d["n5"] >= min_n5)].sort_values(["sym", "session"])
    out = []
    for sym, p in panel.groupby("sym", sort=False):
        g = d[d["sym"] == sym]
        dates = g["session"].to_numpy("datetime64[ns]")
        cums = {c: np.concatenate([[0.0], np.cumsum(g[c].to_numpy(float))]) for c in ["rv5", "bv5", "rv1", "n5"]}
        t = p["date"].to_numpy("datetime64[ns]")
        end = t + p["tenor"].to_numpy("int64") * np.timedelta64(1, "D")
        i = np.searchsorted(dates, t, side="right")
        j = np.searchsorted(dates, end, side="right")
        o = pd.DataFrame({"row_id": p["row_id"].to_numpy(), "n_sessions": j - i})
        for c, cs in cums.items():
            o[f"{c}_sum"] = cs[j] - cs[i]
        out.append(o)
    f = pd.concat(out, ignore_index=True) if out else pd.DataFrame()
    with np.errstate(invalid="ignore", divide="ignore"):
        f["rvol5"] = np.sqrt(252 * f["rv5_sum"] / f["n_sessions"].where(f["n_sessions"] > 0))
        f["rvol1"] = np.sqrt(252 * f["rv1_sum"] / f["n_sessions"].where(f["n_sessions"] > 0))
    return f.sort_values("row_id").reset_index(drop=True)


class Running:
    """The incremental computation in q/live.q, for checking it against measures()."""

    def __init__(self, cal):
        self.cal = cal
        self.st = {}
        self.acc = {}

    def _close(self, s):
        x = self.st[s]
        if not pd.isna(x["prev_close"]) and x["bucket"] - x["prev_bucket"] <= GAP_MAX:
            r = np.log(x["last_close"]) - np.log(x["prev_close"])
            ses = session_of(self.cal, [x["bucket"]])[0]
            if not pd.isna(ses):
                bv = np.pi / 2 * abs(r) * abs(x["prev_r"]) if ses == x["prev_session"] else 0.0
                n, rv, b = self.acc.get((s, ses), (0, 0.0, 0.0))
                self.acc[(s, ses)] = (n + 1, rv + r * r, b + bv)
                x["prev_r"], x["prev_session"] = r, ses
        x["prev_bucket"], x["prev_close"] = x["bucket"], x["last_close"]

    def on_bar(self, s, t, c):
        b = (t - ONE_NS).floor(K5) + K5
        x = self.st.get(s)
        if x is None:
            self.st[s] = {"bucket": b, "last_close": c, "prev_bucket": pd.NaT, "prev_close": np.nan,
                          "prev_r": np.nan, "prev_session": None}
        elif b > x["bucket"]:
            self._close(s)
            x["bucket"], x["last_close"] = b, c
        else:
            x["last_close"] = c

    def flush(self):
        for s in self.st:
            self._close(s)

    def table(self):
        rows = [(s, ses, n, rv, bv) for (s, ses), (n, rv, bv) in self.acc.items()]
        return pd.DataFrame(rows, columns=["sym", "session", "n", "rv", "bv"]).sort_values(["sym", "session"]).reset_index(drop=True)
