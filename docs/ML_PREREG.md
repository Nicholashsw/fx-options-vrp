# Pre-registration: realised-vol forecasting layer (steps 15–16)

Written and committed before any test-period (2013 onward) forecast or strategy
result was computed. Everything below is fixed; deviations, if any, are listed
in the "Deviations" section at the bottom with the reason, and nothing is tuned
on the test period. Every variant listed in §6 is reported, including losers.

What was already known when this was written: the existing in-sample results of
steps 11–13 (in particular xs_top1_iv_z_by_date_tenor, mean 0.5126, NW63 t
2.4139 over 2010–2026). No forecast of any kind had been fitted.

## 1. Question

Does a better forecast of forward realised volatility raise the t-statistic of
the leak-free cross-sectional short-vol rule? Predicted VRP is defined as
IV_t − RV_forecast_t and replaces the trailing IV z-score as the ranking signal.
Either answer is a result.

## 2. Sample and target

- Unit: the step-11 daily cell (date, economic_root, target_tenor), with the
  same rules (rv_status == "ok", 6N from 2014-01-01, equal-weight mean of the
  selected ATM contracts in the cell).
- Target: y = log(realized_vol), where realized_vol is the step-10/11 forward
  realised vol over (t, t+H], H = 30/60/90 calendar days, from the option's own
  underlying futures contract. The step-15 rebuild must reproduce the step-11
  realized_vol and black76_iv cell values exactly (asserted).
- Modelling sample: cells where every feature in §3 that cannot be imputed is
  available (HAR terms and iv_z). The same sample is used by every model, so
  all forecasts are compared on identical rows.

## 3. Features (all known at the close of t)

Built at option level from `futures_returns.parquet` of the option's own
`future_symbol` (returns dated ≤ t), then aggregated to the cell by
equal-weight mean exactly as step 11 aggregates realized_vol:

| Feature | Definition |
|---|---|
| har_d | log of sqrt(252 · r²) for the latest return dated ≤ t; that return must be dated ≥ t − 5 calendar days |
| har_w | log of sqrt(252 · mean r² over the latest 5 returns ≤ t); oldest of the 5 dated ≥ t − 14 cd |
| har_m | log of sqrt(252 · mean r² over the latest 22 returns ≤ t); oldest of the 22 dated ≥ t − 45 cd |
| log_iv | log(black76_iv) of the cell |
| iv_slope | black76_iv(30d) − black76_iv(90d) for the same (date, root), assigned to all tenors of that root-date; if either tenor is missing, set to 0 with iv_slope_missing = 1 |
| iv_z | step-12 trailing z-score (252-obs window ending t−1, min 126), recomputed with the identical formula |
| root, tenor | one-hot identifiers (XGBoost, LSTM) |

Option-level trailing variances are floored at 1e-6 (0.1% vol) before the log
(zero-change settlement days). The age guards stop a trailing window from
reaching back into a previous decade of the same one-digit-year symbol, or
across a long gap. The trailing vols are averaged over the cell's contracts first
and the log is taken after, mirroring how realized_vol is built.

## 4. Models

Fixed seed 15 throughout (numpy, xgboost, torch).

1. **IV**: ŷ = log_iv. The market's forecast; the benchmark to beat. No fit.
2. **HAR**: OLS of y on [1, har_d, har_w, har_m], fitted separately per tenor,
   pooled across roots.
3. **HAR-IV**: OLS of y on [1, har_d, har_w, har_m, log_iv], per tenor, pooled
   across roots.
4. **XGB**: XGBoost regressor, one model pooled across roots and tenors, all §3
   features. Fixed hyperparameters (not tuned): objective reg:squarederror,
   tree_method hist, max_depth 4, learning_rate 0.03, subsample 0.8,
   colsample_bytree 0.8, min_child_weight 20, reg_lambda 1, n_estimators up to
   2000 with early stopping (100 rounds) on the validation slice.
5. **LSTM**: one layer, hidden size 16, pooled across roots and tenors. Input
   is the sequence of the last 22 cells of the same (root, tenor) series up to
   and including t (left zero-padded when shorter), each step carrying the
   standardised continuous features (har_d, har_w, har_m, log_iv, iv_slope,
   iv_slope_missing, iv_z); the final hidden state is concatenated with the
   root and tenor one-hots and mapped to ŷ by a linear layer. Target
   standardised with training statistics. Adam, lr 1e-3, batch 512, MSE loss,
   up to 100 epochs, early stopping with patience 8 on the validation slice,
   best-epoch weights restored. CPU, deterministic algorithms on.

Controls and references (reported, not candidates):

- **SHUF**: model 4 with identical settings, but the training-window target
  (fit and validation slices) randomly permuted (seed 15 + refit index).
  Pass criterion: pooled out-of-sample Mincer-Zarnowitz R² ≤ 0.01 and not
  significantly better than TRAINMEAN (one-sided DM on squared error, 5%).
  Failure means the pipeline leaks and the study stops.
- **TRAINMEAN**: per-tenor training-window mean of y. Defines "chance" for SHUF.

## 5. Walk-forward protocol and leakage controls

- Trading days = sorted unique dates of the daily panel. First refit date =
  first trading day ≥ 2013-01-01; then every 63rd trading day. Each fit
  predicts the test block [T_k, T_{k+1}). Expanding window from the start of
  the modelling sample.
- Purge / embargo: a training row dated t with tenor H is kept only if
  t + H calendar days < T_k, i.e. its whole target window has closed before the
  refit date.
- Validation slice (XGB, LSTM, SHUF): the training rows dated on or after the
  85th percentile of training dates. Rows used for fitting must additionally
  satisfy t + H < start of the validation slice (the same embargo inside the
  training window).
- Standardisation (XGB, LSTM, SHUF): continuous features scaled with the
  mean/sd of the fit rows of that refit only.
- If the first training window turns out too thin (fewer than 2,000 rows) the
  first test date moves to the first refit date at which it is not, and that is
  reported.

## 6. Forecast evaluation

Out-of-sample rows only (all test blocks), identical rows for every model.

- Metrics per (root, tenor), per tenor and pooled:
  RMSE of log RV; QLIKE = σ²/h − log(σ²/h) − 1 with σ² = realized_vol² and
  h = exp(2ŷ); Mincer-Zarnowitz regression y = a + b·ŷ, report a, b, R².
- Diebold-Mariano of each model vs IV and vs HAR, for squared error on log RV
  and for QLIKE: loss differential averaged per date over the cells of the
  group, Newey-West t on the mean (the step-13 `nw_t`), lag = H in trading days
  (21/41/62 for 30/60/90d; 62 for groups that pool tenors). Two-sided normal
  p-values. Negative DM statistic = model has lower loss than the benchmark.

## 7. Strategy test (step 16)

Universe: out-of-sample cells of the modelling sample (every cell has iv_z and
every model's forecast). Payoff per selected cell = realised vrp_vol_spread
(step-12 payoff proxy); daily payoff = equal-weight mean across selected cells
(i.e. across tenors); dates with no selected cell do not enter the series
(step-12 convention). Payoffs in vol points.

For each model m in {HAR, HAR-IV, XGB, LSTM, SHUF}, predicted VRP =
black76_iv − exp(ŷ_m):

- `ml_top1_<m>`: per (date, tenor) short the single root with the highest
  predicted VRP (ties: first in root order).
- `ml_top1_pos_<m>`: same pick, kept only if its predicted VRP > 0.

IV is excluded: its predicted VRP is identically zero and cannot rank.

Baselines on the identical universe:

- `xs_top1_iv_z` on the same cells (per (date, tenor) highest iv_z), the
  reference for every `ml_top1_*` (identical date set by construction).
- For each `ml_top1_pos_<m>`, `xs_top1_iv_z` restricted to that variant's dates.
- Context: the published step-12 `xs_top1_iv_z_by_date_tenor` series over
  the same test dates. The step-16 implementation of `xs_top1_iv_z` must
  reproduce the published series exactly on the full step-11 sample (asserted).

Reported for every series: n_days, mean, median, % positive, NW t at 5/21/63,
non-overlapping 21-day t (step-13 functions), skew, excess kurtosis, mean and
NW63 t ex-2022, and mean by calendar year. Paired test: daily difference
(variant − matching baseline) on common dates, mean and NW63 t.

Primary comparison: `ml_top1_xgb` vs `xs_top1_iv_z`. Everything else is
secondary; with 8 candidate variants the reader should discount the best of
them accordingly.

## 8. Outputs

- `$FX_VRP_WORK/clean_v3/vrp_v3/ml_step15/`: forecasts parquet (licensed, stays
  outside the repo), forecast metrics and DM tables (CSV), refit log, figure.
- `$FX_VRP_WORK/clean_v3/vrp_v3/ml_step16/`: daily ML strategy payoffs (parquet),
  summary, yearly and paired-difference tables (CSV), figure.
- Aggregate CSVs copied to `results/ml/`, figures to `paper/figs/`.

## Deviations

1. **SHUF pass criterion (recorded after step 15, before step 16 was run).**
   SHUF scored a pooled out-of-sample MZ R² of 0.0139 against the ≤ 0.01
   threshold, so the criterion as written failed; the DM half passed (one-sided
   p = 0.56 vs TRAINMEAN). The threshold was miscalibrated: TRAINMEAN, which
   uses no features at all, scores 0.0112, because the expanding-window
   intercept moves from one refit block to the next and the realised-vol level
   moves with it. Decomposed by refit block × tenor, SHUF's within-block R² is
   0.00004 and its per-block correlation with the target averages −0.008
   (t = −0.40 over 54 blocks); all of its R² comes from block-level intercepts,
   exactly as for TRAINMEAN. This is read as no leakage, and step 16 proceeds.
   The original criterion and the failure are reported as they are. A correctly
   calibrated version of the test would have been "within-block R² ≈ 0 and not
   better than TRAINMEAN".
