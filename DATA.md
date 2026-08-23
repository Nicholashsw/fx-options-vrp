# Data

## Source

Databento, dataset `GLBX.MDP3` (CME Globex), schemas `statistics` and `definition` only. End-of-day
settlements and open interest; no tick data.

| Job | Role | Symbols (stype_in = parent) | Range |
|---|---|---|---|
| GLBX-20260629-4P8XHGDMJ7 | futures definitions | 6A/6B/6C/6E/6J/6N/6S `.FUT` | 2010-06-06 → 2026-06-29 |
| GLBX-20260629-FXFLMWUFLY | futures statistics | same | same |
| GLBX-20260629-X68TBUTCRX | legacy option statistics | 6A…6S `.OPT` | same (2017-09 and 2018-08 empty at source) |
| GLBX-20260629-YL7YLPP4KC | legacy option definitions | same | same |
| GLBX-20260701-4WHE5FEFQC | post-migration option statistics | ADU/GBU/CAU/EUU/JPU/CHU `.OPT` | 2017-07-01 → 2026-06-29 |
| GLBX-20260701-NCYF7VCH3Q | post-migration option definitions | same | same |

Fields used: settlement (stat_type 3), open interest (stat_type 9); bid/ask (stat_type 7/8) reserved
for cost analysis. 6R (RUB) excluded deliberately.

## What is not in this repository, and why

Databento's licence permits use of the data for research but not redistribution. Nothing derived
at the observation level is committed:

- raw `*.dbn.zst` job folders (11 GB)
- `parquet/` conversions and `clean_v3/` monthly panels (32.5 million rows)
- the ATM export (440,467 rows), the research panel (430,630), the option-level VRP panel, and the
  daily (date, root, tenor) panel (70,714 rows)

`.gitignore` blocks every parquet and DBN file so they cannot be committed by accident.

## What is committed

Aggregated statistics only: per-root and per-tenor medians, yearly medians, the twelve-strategy
robust summary, coverage and validation diagnostics, the seven charts, the report and the paper.
These are the same tables printed in the paper. The largest committed table,
`diagnostics/coverage_roots_monthly.csv`, is a per-role, per-month, per-root **row count** — no
settlement, price or open-interest value from any individual instrument is committed anywhere.
`diagnostics/inventory_summary.csv` lists the Databento job IDs and file counts so the pull can be
reproduced; it carries no market data.

## Re-creating the panel

Submit the six jobs above (or equivalent ranges) from your own Databento account and place the
`GLBX-*` job folders under one directory. Point `DATABENTO_BASE` at that directory and
`FX_VRP_WORK` at the working directory the pipeline should build into (conventionally
`$DATABENTO_BASE/fx_vrp_work`), then run `scripts/00_inventory.py` through
`14_charts_tables.py`. Expected row counts at every stage are in `README.md` and
`diagnostics/reproduction_scorecard.csv`; `REPRO.md` gives the full working-directory layout and
the checkpoints for the analysis layer.
