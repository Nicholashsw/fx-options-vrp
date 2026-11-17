# REPRO: rebuilding the panel and the checkpoints to hit

This repository ships **code and aggregated results only**. The Databento
panels are licensed market data and are not redistributed, so nothing here can
be re-run against data that is already in the repo: you rebuild the panels from
your own Databento pull (see [`DATA.md`](DATA.md) for the six job
specifications) and check the run against the checkpoints below.

## Working directory

Scripts live in `scripts/`. They read and write a **working directory outside
this repository**, supplied through environment variables:

| Variable | Used by | Points at |
|---|---|---|
| `DATABENTO_BASE` | steps 00–01 | the directory that contains the six `GLBX-*` job folders |
| `FX_VRP_WORK` | steps 00–10 and `run.py` (steps 11–16) | the working directory for every derived artefact |

```
export DATABENTO_BASE=/path/to/databento          # holds the GLBX-2026... job folders
export FX_VRP_WORK=$DATABENTO_BASE/fx_vrp_work    # holds parquet/, clean_v3/, diagnostics/
```

Set both explicitly. Unset, `DATABENTO_BASE` falls back to the repository's
parent directory. `FX_VRP_WORK` then falls back to `fx_vrp_work` beside the
repository in steps 00 and 01, and to the repository root in steps 02 to 10,
where a run would overwrite the committed `diagnostics/` files. `run.py` stops with a message
when it is unset.
The working directory grows to tens of gigabytes.

The pipeline creates:

```
$FX_VRP_WORK/
  diagnostics/            inventory, coverage audits, validation scorecard
  parquet/                step-01 conversions (fut/opt x defs/stats)
  clean_v3/
    panel_monthly/        193 monthly joined panels
    atm_export_v3/     ATM panel (440,467 rows)
    iv_v3/                Black-76 IV + research panel (430,630 rows)
    vrp_v3/
      vrp_panel_v3.parquet     option-level VRP panel (430,630 rows)
      daily_panel_step11/      daily panel (70,714 rows)
      strategy_step12/         daily payoff proxies
      robust_stats_step13/     robust_strategy_summary_v3.csv
      charts_step14/           the 7 charts, 200 dpi
      tables_step14/           tables 1-4
```

The committed `diagnostics/`, `results/` and `paper/figs/` in this repository
are snapshots of `$FX_VRP_WORK/diagnostics/`, of `robust_stats_step13/` +
`tables_step14/`, and of `charts_step14/` (the charts are committed once, under
`paper/figs/`, where the TeX source expects them). Diff a fresh run against them.

## Full rebuild (steps 00–14)

Python 3.10–3.12 (3.12 recommended; **do not use 3.14**, DBN conversion
crashes) with the packages in `requirements.txt`.

```
python scripts/00_inventory.py             # reads $DATABENTO_BASE
python scripts/01_convert.py --budget 30   # DBN.ZST -> parquet; 30 seconds a call, repeat until it prints ALL_DONE
python scripts/02_coverage_audit.py        # steps 02-10 use $FX_VRP_WORK only
python scripts/03_join_diagnostic.py
python scripts/04_build_clean_v3.py --budget 30
python scripts/05_validate_clean_v3.py
python scripts/06_atm_export.py            # monthly picks; repeat until ALL_DONE
python scripts/06_atm_export.py --finalize # writes atm_export_v3/, which step 07 reads
python scripts/07_black76_iv.py
python scripts/08_research_panel.py
python scripts/09_futures_settle_series.py            # monthly parts; repeat until ALL_DONE
python scripts/09_futures_settle_series.py --finalize # writes the settle and return series step 10 reads
python scripts/10_vrp.py
```

Steps 01, 02, 04, 06 and 09 are long and take `--budget <seconds>` (default
30). Each call works for that long and stops: call them repeatedly until they
print `ALL_DONE`. Steps 06 and 09 then need one more call with `--finalize`.

## Analysis layer only (steps 11–16)

Once `$FX_VRP_WORK/clean_v3/vrp_v3/` holds the step-10 outputs
(`vrp_panel_v3.parquet`, 430,630 rows, plus `futures_returns.parquet` and
`futures_settle_daily.parquet`), the analysis layer reruns on its own in
minutes and touches nothing under `clean_v3/panel_monthly`:

```
python run.py                          # daily, strategy, stats, figures, rvforecast, rvstrategy, in order
python run.py --from stats --to figures    # a sub-range; the stage names are daily, strategy, stats, figures, rvforecast, rvstrategy
python -m pytest -q                    # with FX_VRP_WORK set, also checks the checkpoints below
```

The stages write the daily panel (expect 70,714 rows), the 12 payoff-proxy series,
`robust_strategy_summary_v3.csv`, and the 7 charts and tables 1-4. The notebook is not rebuilt by
a run: it draws the committed files in `results/`.

## Expected checkpoints

- Step 11 prints `6N pre-2014 rows dropped: 3,526` and
  `daily panel rows: 70,714`, date range 2010-06-04 .. 2026-06-08.
- Step 13 prints a 12-row table whose first row
  (static_all_roots_all_tenors) shows mean 0.2766, median 0.4925,
  t_nw63 1.7906; xs_top1_iv_z_by_date_tenor shows mean 0.5126,
  t_nw63 2.4139, t_nonoverlap21 2.7073.
- `tests/test_checkpoints.py` checks the daily row count and the figures above when
  `FX_VRP_WORK` is set. The notebook reads only `results/` and recomputes nothing.
- `diagnostics/reproduction_scorecard.csv` records the equivalent comparison
  for steps 00 to 10 against an earlier build. That build's figures are typed
  into the scripts as targets and the build itself is not kept.

## Rebuilding the paper PDF

Requires TeX Live with `pdflatex`:

```
cp "$FX_VRP_WORK"/clean_v3/vrp_v3/charts_step14/*.png paper/figs/
cd paper && pdflatex vrp_paper.tex && pdflatex vrp_paper.tex
```

## What is not here

Raw data (11 GB of DBN.ZST across six Databento jobs) and every multi-GB
parquet intermediate stay outside the repository, under `$DATABENTO_BASE` and
`$FX_VRP_WORK`. `.gitignore` blocks them so they cannot be committed by
accident.
