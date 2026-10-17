# q: intraday realised volatility

Step 10 measures each option's forward realised volatility from daily settlement returns of its own futures contract: about 21 squared returns for a 30-day option. That estimator is unbiased for variance but noisy, and realised volatility is its square root, so the noise biases volatility down and the IV − RV spread up, by more at short tenors where there are fewer returns. This folder rebuilds the realised leg from one-minute futures bars in kdb+/q, so the premium can be measured with a far more precise estimator on the same option rows.

The q code stores the bars in a date-partitioned HDB, computes five- and one-minute realised variance and bipower variation per contract and settlement session, and sums them over each option's (t, t+H] window with a window join. A small tickerplant, subscriber and feed handler run the same measures in real time on replayed bars.

## Files

| File | What it does |
|---|---|
| `rv.q` | The library: CME settlement times (14:00 Chicago, so 19:00 or 20:00 UTC with US daylight saving), session assignment by `binr` on the settlement calendar, 5-minute sampling by `xbar`, returns, realised variance, bipower variation, and `.rv.forward`, the `wj1` window join |
| `build_hdb.q` | Monthly bar CSVs into an HDB partitioned by the UTC date of each bar's close, `p#` on `sym` |
| `daily_rv.q` | HDB to `rv_daily.csv`: one row per contract and session, month by month with a four-day lead-in |
| `fwd_rv.q` | `rv_daily.csv` and the option rows to `fwd_rv.csv`, one row per option |
| `live.q` | The same measures computed one bar at a time; after a flush it equals the batch result |
| `tick/tick.q`, `tick/rdb.q`, `tick/feed.q` | Tickerplant (logs every update, publishes to subscribers), real-time subscriber running `live.q`, and a replay feed |
| `tests/test_rv.q` | Calendar, sessions, measures on a known path, the gap guard, incremental against batch, window edges |

`scripts/intraday_rv.py` is a pandas implementation of every function in `rv.q` and `live.q`, held to the same test cases in `tests/test_intraday_rv.py`.

## Conventions

- A bar is stamped with its **close** (step 15 adds the minute to Databento's open stamp), and the five-minute sample is the last close in each bucket, labelled by the bucket's end.
- A return belongs to the **session in which it ends**, and nothing resets at a session boundary: each session's first return starts from the previous session's last sample. A session's sum therefore runs from one settlement to the next, the same span as the settlement-to-settlement return in step 10, including the daily halt and the weekend gap.
- Sessions come from the settlement calendar of step 9, so exchange holidays need no special handling.
- A return spanning more than four days is dropped; a session needs 100 five-minute returns (of about 276 in 23 Globex hours) to count in a forward window, which keeps out thin back months.
- Forward volatility is annualised as in step 10: sqrt(252 × sum of daily variance / sessions).

## Run

```bash
export FX_VRP_WORK=...                                 # as for steps 0-14
python scripts/15_intraday_bars.py --plan              # Databento quote per month; nothing downloaded
python scripts/15_intraday_bars.py --budget 60 --max-cost 40
python scripts/16_intraday_rv.py --export-panel

q q/build_hdb.q -bars $FX_VRP_WORK/intraday/bars -hdb $FX_VRP_WORK/intraday/hdb
q q/daily_rv.q  -hdb $FX_VRP_WORK/intraday/hdb -cal $FX_VRP_WORK/intraday/settle_calendar.csv \
                -out $FX_VRP_WORK/intraday/rv_daily.csv
q q/fwd_rv.q    -rv $FX_VRP_WORK/intraday/rv_daily.csv -panel $FX_VRP_WORK/intraday/panel_for_q.csv \
                -out $FX_VRP_WORK/intraday/fwd_rv.csv

python scripts/16_intraday_rv.py --check 2019-03       # q against pandas, one month
python scripts/16_intraday_rv.py                       # both panels and the diagnostics
for v in settlematched intraday; do
  for s in 11_daily_panel 12_strategy_proxy 13_robust_stats; do FX_VRP_VARIANT=$v python scripts/$s.py; done
done
python scripts/17_rv_estimator_compare.py
```

`python scripts/16_intraday_rv.py --engine python` computes everything in pandas instead of q, which is slower but needs no kdb+ licence; the free KDB-X Community Edition runs the q side.

Real time, in three terminals:

```bash
q q/tick/tick.q -p 5010
q q/tick/rdb.q  -p 5011 -tp localhost:5010 -cal $FX_VRP_WORK/intraday/settle_calendar.csv
q q/tick/feed.q -tp localhost:5010 -bars $FX_VRP_WORK/intraday/bars/2024-03.csv
```

then `h:hopen 5011; h".live.view[]"` for the running volatility per contract and session.

## Tests

```bash
q q/tests/test_rv.q
python -m pytest tests -q
```

## Status

The pandas reference runs and passes its tests here, and the whole pipeline (steps 15 to 17) has been run end to end on synthetic files. The q code was written without access to a kdb+ licence and has not been executed yet: the first run should be `q q/tests/test_rv.q`, then `16_intraday_rv.py --check` on a month of real data. No result from this leg is in the paper or the report until both pass.
