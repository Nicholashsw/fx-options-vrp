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
| `FX_VRP_WORK` | steps 00–14 and `build_notebook.py` | the working directory for every derived artefact |

```
export DATABENTO_BASE=/path/to/databento          # holds the GLBX-2026... job folders
export FX_VRP_WORK=$DATABENTO_BASE/fx_vrp_work    # holds parquet/, clean_v3/, diagnostics/
```

Unset, `DATABENTO_BASE` falls back to the repository's parent directory and
`FX_VRP_WORK` to the repository root. Set both explicitly for a real run: the
working directory grows to tens of gigabytes and must not land inside the repo.

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
  notebooks/              vrp_analysis.ipynb, written and executed by build_notebook.py
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
python scripts/01_convert.py --budget 30   # DBN.ZST -> parquet; repeat until it prints ALL_DONE
python scripts/02_coverage_audit.py        # steps 02-14 use $FX_VRP_WORK only
python scripts/03_join_diagnostic.py
python scripts/04_build_clean_v3.py --budget 30
python scripts/05_validate_clean_v3.py
python scripts/06_atm_export.py
python scripts/07_black76_iv.py
python scripts/08_research_panel.py
python scripts/09_futures_settle_series.py
python scripts/10_vrp.py
```

Steps 01, 02, 04, 06 and 09 are long and take `--budget <minutes>`. They are
resumable: call them repeatedly until they report completion.

## Analysis layer only (steps 11–14 and the notebook)

Once `$FX_VRP_WORK/clean_v3/vrp_v3/` holds the step-10 outputs
(`vrp_panel_v3.parquet`, 430,630 rows, plus `futures_returns.parquet` and
`futures_settle_daily.parquet`), the analysis layer reruns on its own in
minutes and touches nothing under `clean_v3/panel_monthly`:

```
python scripts/11_daily_panel.py       # daily panel, expect 70,714 rows
python scripts/12_strategy_proxy.py    # 12 payoff-proxy series
python scripts/13_robust_stats.py      # robust_strategy_summary_v3.csv
python scripts/14_charts_tables.py     # 7 charts + tables 1-4
python scripts/build_notebook.py       # rebuild + execute the notebook
```

## Expected checkpoints

- Step 11 prints `6N pre-2014 rows dropped: 3,526` and
  `daily panel rows: 70,714`, date range 2010-06-04 .. 2026-06-08.
- Step 13 prints a 12-row table whose first row
  (static_all_roots_all_tenors) shows mean 0.2766, median 0.4925,
  t_nw63 1.7906; xs_top1_iv_z_by_date_tenor shows mean 0.5126,
  t_nw63 2.4139, t_nonoverlap21 2.7073.
- The notebook's final cell asserts equality between its own recomputation
  and the step 12/13 outputs and prints
  `All 12 strategies match the pipeline outputs (mean and NW63 t).`
- `diagnostics/reproduction_scorecard.csv` records the equivalent comparison
  for steps 00–10 against the original build.

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
