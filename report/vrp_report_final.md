# Volatility Risk Premia and High-Implied-Volatility Selection in CME G10 FX Options on Futures

*Nicholas Hong, Nanyang Technological University*

---

## Abstract

This study constructs a research-grade panel of CME G10 FX options on futures from June 2010 to June 2026 and tests whether option implied volatility systematically exceeds subsequent realized volatility. The dataset covers seven FX futures roots (6A, 6B, 6C, 6E, 6J, 6N, 6S) at 30, 60, and 90 day target tenors, built from Databento GLBX.MDP3 statistics and definition schemas. A key data contribution is the correction of the 2017 CME FX options symbol migration, in which several legacy American-style option families were sunset and replaced by expiration-only European-style contracts under new symbols; failing to account for this creates an apparent post-2017 data discontinuity. A second data contribution is the identification and removal of a structurally anomalous legacy 6N (NZD) implied volatility regime that persists through 2013: settlement prints implying 30 to 40 percent volatility against roughly 8 percent realized, on contracts with zero open interest.

Using Black-76 implied volatility and forward realized volatility computed from the specific underlying futures contract of each option, the final daily panel contains 70,714 root-tenor observations. A static short-volatility payoff proxy across all roots and tenors yields a mean implied-minus-realized volatility spread of 0.28 volatility points (median 0.49, positive on 65.6 percent of days) with a Newey-West 63-lag t-statistic of 1.79 and a non-overlapping-sample t-statistic of 2.27. Conditioning on high implied volatility strengthens the result: selecting the root with the highest leak-free trailing implied-volatility z-score by date and tenor raises the mean spread to 0.51 volatility points (median 0.76, positive 67.2 percent) with an NW63 t-statistic of 2.41 and a non-overlapping-sample t-statistic of 2.71. The improvement is concentrated in the cross-sectional selection family; time-series threshold rules add little once the z-score is restricted to trailing information. The premium is persistent but time-varying and left-skewed: 2022 is a broad stress year in which short volatility loses across all seven roots. The results are payoff proxies rather than executable P&L and exclude transaction costs, delta hedging, and margin.

---

## 1. Introduction

### 1.1 Motivation

Foreign exchange options are used by corporates, macro funds, real-money investors, and market makers to manage currency risk. Option prices embed expectations of future volatility, but they may also embed compensation for bearing volatility risk. If implied volatility is systematically higher than the volatility subsequently realized, sellers of options earn a volatility risk premium (VRP) on average, in exchange for absorbing losses during volatility spikes.

This project asks three questions of CME G10 FX options on futures:

1. Does implied volatility systematically exceed subsequent realized volatility?
2. Is the premium stronger when implied volatility is high relative to its own history?
3. Does a simple high-IV selection rule improve a short-volatility payoff proxy?

### 1.2 Contribution

The project contributes in three ways.

First, it builds a cleaned, exchange-level CME FX options on futures dataset spanning 2010 to 2026, including a documented correction for the 2017 CME FX options symbol migration. This correction is necessary for any long-horizon study of these markets, because the legacy American-style option symbols were sunset in mid-2017 and replaced by expiration-only European-style contracts under new roots. The cleaning also identifies and removes an anomalous legacy 6N implied volatility regime that extends through 2013.

Second, it computes Black-76 implied volatility and forward realized volatility from the specific underlying futures instrument referenced by each option, allowing a direct, contract-consistent construction of the volatility risk premium.

Third, it tests both unconditional and conditional short-volatility payoff proxies, with robust inference (Newey-West corrections at multiple lags and non-overlapping sampling), a strictly leak-free conditioning signal, and full disclosure of every strategy variant tested, so that the conditional result can be judged against the specification-search alternatives.

### 1.3 Main findings

1. FX option implied volatility generally exceeds subsequent realized volatility. The median IV-RV spread is positive for six of seven roots.
2. JPY (6J) shows the strongest median VRP at 0.87 volatility points; NZD (6N) is approximately flat (median -0.03 from 2014 onward) and is also the thinnest market in the sample.
3. Among static tenor strategies, 30 days is strongest (NW63 t = 2.40); 60 and 90 day static results are positive but not robustly significant on their own.
4. Conditioning on high implied volatility improves the payoff proxy, but the improvement is concentrated in the cross-sectional rule: selecting the top-IV-z-score root per date and tenor raises the static mean spread from 0.28 to 0.51 volatility points and strengthens robust significance. Time-series threshold rules (sell only when a cell's own z-score is high) add little once the z-score uses only trailing information.
5. The payoff distribution is left-skewed in every variant: for the static strategy the mean spread (0.28) is well below the median (0.49), with skewness -1.69 and excess kurtosis 7.0. This is the defining risk profile of short volatility, and 2022 is the clearest realization of that tail.

---

## 2. Literature Review

### 2.1 The volatility risk premium

The volatility risk premium is the gap between option-implied volatility and subsequently realized volatility. In variance form:

VRP_var,t = IV_t^2 - RV_{t,t+h}^2

A positive VRP means implied variance exceeded future realized variance, so a delta-hedged option seller would, on average, have collected more premium than the volatility they had to pay out.

### 2.2 Why the premium may exist

Several mechanisms can generate a persistent VRP: hedging demand from investors who are structurally long risk and buy protection, crash-insurance demand that pushes up out-of-the-money and hence overall implied levels, risk aversion to volatility states in which marginal utility is high, limits to arbitrage and intermediary balance sheet constraints that prevent premium compression, and simple compensation for the negatively skewed payoff profile of volatility selling.

### 2.3 The FX setting

FX differs from equities in ways that make the FX VRP an interesting object of study. There is no obvious long-only risk premium analogous to the equity premium, so FX volatility pricing is less anchored by a directional hedging channel. FX volatility is tightly linked to macro uncertainty: monetary policy divergence, rate differentials, carry unwinds, and risk sentiment. Safe-haven currencies such as JPY and CHF may carry structurally different volatility demand, since they appreciate in stress and their options serve as macro hedges. The finding in this study that JPY options command the largest median VRP is consistent with that hedging-demand channel.

### 2.4 Related strategy concepts

The strategies tested here connect to the broader literature on short volatility and variance risk premia, volatility timing (selling volatility conditionally rather than unconditionally), carry-style premia harvesting, and macro stress regimes as the periods in which such premia reverse.

---

## 3. Data

### 3.1 Dataset

- Source: Databento GLBX.MDP3 (CME Globex market data), 6 batch jobs, 986 DBN.ZST files, roughly 11 GB raw
- Instruments: CME FX options on futures and their underlying FX futures
- Schemas: statistics (settlements, open interest, bid, ask) and definition (contract metadata)
- Sample: 2010-06-04 to 2026-06-08 in the final daily VRP panel
- Roots: 6A (AUD), 6B (GBP), 6C (CAD), 6E (EUR), 6J (JPY), 6N (NZD), 6S (CHF)
- Target tenors: 30, 60, 90 days
- Final daily panel: 70,714 root-tenor-date observations

### 3.2 Required fields

From the statistics schema: settlement price (stat_type 3) and open interest (stat_type 9, value in the quantity field). The main pipeline uses settlements, open interest, and definitions; resting bid and ask statistics (stat_types 7 and 8) are identified for future transaction-cost analysis but are not processed in this pass.

From the definition schema: instrument_id, raw_symbol, expiration, strike price, option type, underlying_id, and contract multiplier.

### 3.3 The 2017 CME FX options symbol migration

A central data challenge is that CME sunset several legacy FX options families in 2017. The legacy contracts were American-style with early exercise; their replacements are expiration-only European-style contracts listed under new symbols. A naive symbol-based query therefore shows an apparent post-2017 gap or discontinuity in the legacy roots. This was confirmed with Databento support.

The migration mapping is:

| New symbol (post 2017-07) | Economic root | Currency |
|---|---|---|
| ADU | 6A | AUD |
| GBU | 6B | GBP |
| CAU | 6C | CAD |
| EUU | 6E | EUR |
| JPU | 6J | JPY |
| CHU | 6S | CHF |
| 6N (unchanged) | 6N | NZD |

Sample construction logic: before 2017-07, the legacy roots 6A, 6B, 6C, 6E, 6J, 6S, and 6N are used. From 2017-07 onward, the migrated symbols ADU, GBU, CAU, EUU, JPU, and CHU are used and mapped back to their economic roots, while 6N continues under its original symbol. Legacy non-6N symbols are excluded after 2017-07 to avoid double counting.

### 3.4 Cleaning and join rules

Definition files contain repeated intraday updates per instrument, so raw definitions cannot be joined directly without creating many-to-many join explosions. The pipeline therefore sorts definitions by ts_event and deduplicates by instrument_id (keep last). Option and futures settlements are filtered to stat_type 3, dated from ts_ref with ts_event fallback, and deduplicated by (date, instrument_id). Options are joined to their underlying futures through the definition-level underlying_id, and futures settlements are then joined by date and futures instrument_id. Join diagnostics on representative months (2016-01 legacy, 2024-01 migrated, 2024-01 legacy 6N) show 0 percent missing future symbols and settlements.

The full clean panel contains 32,525,006 option-day rows across 193 monthly files with zero duplicate months and zero source-rule violations. (A prior build of the same pipeline produced 32,525,026 rows; the 20-row difference, 0.00006 percent, is consistent with minor Databento historical reprocessing and has no effect on any downstream panel, all of which reproduce exactly.) A month-boundary overlap initially produced roughly 8,500 duplicate rows in the ATM export; these were removed by a global deduplication and re-rank, yielding a final ATM panel of 440,467 rows with zero duplicates.

### 3.5 ATM tenor selection

The ATM panel applies the following filters: positive option settlement, positive futures settlement, positive strike, days to expiry between 10 and 130, absolute log moneyness at most 0.10, and the top 3 contracts per (date, root, tenor, option type) bucket, ranked by tenor distance, moneyness, and open interest. Each observation is assigned to its nearest target tenor only, with boundary ties going to the outer tenor (a day count of 45 maps to the 30 day tenor and 75 maps to the 90 day tenor, so the 60 day pool is strictly 46 to 74 days). Calls and puts are then aggregated into a daily ATM volatility measure per root and tenor. All quality filters pass with zero violating rows in the final export.

### 3.6 The 6N anomaly

Legacy 6N implied volatility in 2010 through 2013 contains a structurally anomalous regime: repeated settlement prints implying 30 to 40 percent volatility against roughly 8 percent contemporaneous realized volatility, exclusively on contracts with zero open interest. Solver diagnostics rule out inversion failure. Of the 103 daily panel cells sample-wide with implied volatility above 20 percent and zero open interest, 102 are 6N cells in 2013; high-implied days for every other root coincide with genuine stress episodes (2011 euro area crisis, Brexit, the SNB de-peg, COVID). An earlier version of this study excluded 6N before 2013; the finalization pass documented that the anomaly persists through 2013, so 6N enters the sample on 2014-01-01. This removes 3,526 option-level observations. 6N remains the thinnest market in the panel (roughly 78 percent of its daily cells carry zero open interest), which is retained as a caveat on all 6N results.

---

## 4. Methodology

### 4.1 Black-76 implied volatility

Because these are options on futures, Black-76 is the appropriate pricing model. The carry between spot and forward is already embedded in the futures price via covered interest parity, so no separate foreign and domestic rate inputs are needed.

Call: C = e^{-rT} [F N(d1) - K N(d2)]
Put: P = e^{-rT} [K N(-d2) - F N(-d1)]

d1 = [ln(F/K) + 0.5 sigma^2 T] / (sigma sqrt(T)), d2 = d1 - sigma sqrt(T)

where F is the futures settlement, K the strike, T = DTE/365.25, sigma the implied volatility, and r the risk-free rate. In this first pass r = 0, which is a mild approximation affecting only the discount factor on premium, not the volatility content of prices; the focus is on relative IV and the IV-RV spread.

Caveat: pre-2017 legacy contracts are American-style, so Black-76 is an approximation for the older portion of the sample. Early exercise premium biases legacy implied volatilities slightly upward relative to a true American solver, which if anything inflates measured pre-2017 VRP marginally. Post-migration contracts are expiration-only European-style and are priced consistently by Black-76.

The IV solver achieves 99.999 percent valid inversions on the ATM panel (440,462 of 440,467 rows), with 5 rows rejected as below intrinsic value.

### 4.2 Forward realized volatility

For each option observation, forward realized volatility is computed over the calendar window (t, t + H], where H is the target tenor (30, 60, or 90 calendar days), from the settlement series of the specific underlying futures instrument referenced by that option, not merely the FX root. This matters because different options on the same root can reference different delivery months with different settlement dynamics near roll dates.

With log returns r_t = ln(F_t / F_{t-1}) on consecutive settlement observations of the option's own futures contract, realized variance is annualized on a trading-day basis: RV_var = (252 / n) times the sum of squared returns in the window, where n is the number of return observations, and realized volatility is its square root. A gap guard drops return observations spanning more than 14 calendar days, which also neutralizes decade-apart reuse of futures symbols. Each observation carries an rv_status flag (ok, short_span, few_obs, no_data) rather than being silently dropped; rows require a data span of at least 60 percent of the horizon and a minimum return count. Rows failing these requirements (2,856 of 430,630, concentrated at the sample end where the forward window is truncated) are excluded, leaving 427,774 valid VRP observations at the option level (424,248 after the 6N 2013 exclusion). The raw sum of squared returns, return count, and span are stored so alternative annualization conventions can be recomputed.

### 4.3 Volatility risk premium

Two measures are used:

- Variance VRP: VRP_var = IV^2 - RV^2
- Volatility spread: VRP_spread = IV - RV

The volatility spread in annualized volatility points is the headline unit throughout, because it maps intuitively to vega-normalized short-volatility payoff. Option-level observations are aggregated into a daily root-tenor panel (70,714 rows) for all strategy tests.

### 4.4 Strategy payoff proxies

Three families of strategies are tested, all defined on the daily root-tenor panel:

**Static:** sell volatility in a fixed universe every day. Variants: all roots and tenors, 30d only, 60d only, 90d only, ex-6N, and majors only (defined as 6E, 6B, 6J, 6S).

**Time-series signal:** sell only cells whose implied-volatility z-score exceeds a threshold (0, 0.5, or 1.0). The z-score is computed per root-tenor as (IV_t minus the rolling mean of the trailing 252 observations) divided by the rolling standard deviation of the same window, where the window ends at t-1 (the IV series is shifted by one day before the rolling statistics are computed), with a minimum of 126 observations. Only information strictly prior to t is used; there is no look-ahead. Cells without a valid z-score (3.7 percent, at the start of each root-tenor history) are excluded from conditional strategies.

**Cross-sectional selection:** each date and tenor, rank roots by the same leak-free IV z-score and sell the top 1, top 2, or top 3.

All twelve variants are reported in Table 3. Reporting the full set matters because the headline conditional result is the best performer of a strategy search; its statistical significance should be mentally discounted for multiple testing, and disclosure of the losing variants allows the reader to make that adjustment.

These are payoff proxies, defined as the ex-post IV-minus-forward-RV spread of the selected positions (equal-weight across selected cells each day). They are not executable P&L: bid-ask spreads, delta-hedging slippage, margin, capital usage, and option mark-to-market path are all excluded.

---

## 5. Empirical Results

### 5.1 Implied versus realized volatility by root

*(Chart 1: Median implied volatility vs forward realized volatility by FX root)*

Median implied volatility exceeds median forward realized volatility for six of seven roots. The gap is visibly largest for 6J. 6N is the exception, with realized volatility marginally above implied over the (post-2013) sample.

### 5.2 VRP by currency root

*(Chart 2 and Table 1)*

| Root | Median IV | Median RV | Median VRP spread |
|---|---|---|---|
| 6A | 9.84 | 9.36 | 0.56 |
| 6B | 7.98 | 7.78 | 0.64 |
| 6C | 7.00 | 6.68 | 0.53 |
| 6E | 7.55 | 7.30 | 0.51 |
| 6J | 9.07 | 8.21 | 0.87 |
| 6N | 9.33 | 9.81 | -0.03 |
| 6S | 7.71 | 7.44 | 0.39 |

The premium is not uniform across currencies. JPY options command the largest compensation, consistent with structural demand for yen optionality as a macro and risk-off hedge. NZD is flat; its options offered no premium to sellers over this sample, and its market is also by far the thinnest. CHF, the other classical safe haven, shows a positive but below-average premium.

### 5.3 VRP by tenor

*(Chart 3 and Table 2)*

| Tenor | Median VRP spread | Positive VRP days |
|---|---|---|
| 30d | 0.57 | 62.5% |
| 60d | 0.50 | 62.4% |
| 90d | 0.49 | 62.7% |

The premium exists across all tenors and is slightly stronger at the short end, consistent with short-dated options carrying the largest per-unit-time compensation for gap and event risk.

### 5.4 Yearly regimes

*(Chart 4: yearly median VRP heatmap by root)*

The premium is strongly positive in the early sample (2010 to 2012), broadly negative across all seven roots in 2022, and recovers from 2023 through 2026. The 2022 episode coincides with the fastest global rate-hiking cycle in decades, inflation shocks, and large sustained currency trends (notably JPY depreciation), all of which push realized volatility above what options had implied. 6N also shows sharply negative years in 2015 and 2016 (NZD realized volatility exceeded implied during the dairy-price collapse and RBNZ easing cycle), subject to the thin-market caveat of Section 3.6. The premium is therefore best described as persistent but time-varying, with concentrated reversal in macro stress regimes.

### 5.5 Strategy results

*(Chart 5 and Table 3)*

| Strategy | N days | Mean | Median | Positive % | Skew | Ex. kurt | NW63 t | Non-overlap t |
|---|---|---|---|---|---|---|---|---|
| static_all_roots_all_tenors | 3991 | 0.28 | 0.49 | 65.6 | -1.69 | 7.00 | 1.79 | 2.27 |
| static_30d | 3808 | 0.31 | 0.53 | 65.9 | -2.21 | 11.44 | 2.40 | 2.32 |
| static_60d | 3657 | 0.21 | 0.42 | 63.7 | -1.75 | 7.07 | 1.23 | 1.52 |
| static_90d | 3191 | 0.16 | 0.39 | 61.0 | -1.48 | 5.03 | 0.82 | 1.09 |
| static_ex_6N | 3991 | 0.34 | 0.57 | 68.1 | -1.81 | 7.41 | 2.21 | 2.77 |
| static_major_roots_only | 3991 | 0.32 | 0.62 | 67.2 | -1.88 | 7.48 | 1.93 | 2.38 |
| signal_iv_zscore_ge_0 | 2785 | 0.38 | 0.65 | 65.9 | -1.84 | 9.29 | 1.81 | 1.98 |
| signal_iv_zscore_ge_0p5 | 2215 | 0.38 | 0.65 | 64.6 | -1.73 | 8.55 | 1.50 | 1.53 |
| signal_iv_zscore_ge_1 | 1675 | 0.28 | 0.62 | 61.3 | -1.61 | 7.48 | 0.94 | 0.92 |
| xs_top1_iv_z_by_date_tenor | 3861 | 0.51 | 0.76 | 67.2 | -2.33 | 11.61 | 2.41 | 2.71 |
| xs_top2_iv_z_by_date_tenor | 3861 | 0.38 | 0.65 | 67.5 | -2.97 | 18.81 | 2.03 | 2.32 |
| xs_top3_iv_z_by_date_tenor | 3861 | 0.34 | 0.58 | 66.7 | -2.30 | 11.17 | 2.00 | 2.33 |

Four observations. First, the static premium is positive but only marginally significant (NW63 t = 1.79, non-overlapping t = 2.27); within the static family, the 30 day tenor (t = 2.40) and the ex-6N universe (t = 2.21) are the more robust variants, and excluding the flat, illiquid 6N root mechanically helps. Second, cross-sectional high-IV selection improves the payoff proxy: the top-1 rule nearly doubles the static mean (0.51 versus 0.28) with monotone attenuation through top-2 and top-3, which is the pattern expected if the effect is real rather than a single lucky cell. Third, the time-series threshold family does not survive the leak-free z-score: means rise modestly (0.28 to 0.38) but significance falls with the threshold, because high thresholds concentrate the sample into fewer, more volatile days. An earlier draft of this study reported materially stronger conditional results; those were inflated by the 6N 2013 data artifact of Section 3.6, and their removal is a deliberate correction, not a robustness choice. Fourth, the mean is well below the median in every strategy, and skewness is negative in every strategy (static: -1.69 with excess kurtosis 7.0). The payoff distribution offers frequent modest gains punctuated by occasional large losses; the premium is compensation for exactly this tail, and 2022 is its clearest realization.

Because the headline conditional strategy is the best of twelve tested variants, its NW63 t-statistic of 2.41 overstates significance relative to a pre-registered test. The result should be read as suggestive evidence that cross-sectional high-IV conditioning helps, supported by the monotone pattern across ranks, rather than as a precise significance claim for one specific rule.

### 5.6 Cumulative payoff proxy

*(Chart 6)*

The cumulative payoff proxy generally trends upward over the full sample but suffers drawdowns during stress regimes, most notably around 2020 and 2022. The high-IV cross-sectional strategy produces the strongest cumulative profile; the static strategy experiences deeper relative drawdowns. These curves are cumulated payoff proxies, not equity curves of a tradable strategy.

---

## 6. Robustness

### 6.1 Newey-West correction

Forward realized-volatility windows overlap across consecutive observation dates, inducing strong serial correlation in the daily VRP series; naive t-statistics are therefore badly inflated. Newey-West corrections at 5, 21, and 63 lags are applied, with 63 lags (one quarter, matching the longest RV horizon) as the headline. The best conditional strategy declines from a naive t of 12.2 and NW5 t of 5.35 to NW63 t = 2.41, illustrating how much of the naive significance is overlap; the static strategy declines from a naive t of 10.4 to NW63 t = 1.79.

### 6.2 Non-overlapping sampling

As an independent check, each daily payoff series is sampled every 21 observations across all 21 starting offsets, eliminating overlap by construction at the monthly scale. The conditional strategy remains positive with a simple t-statistic of 2.71 averaged across offsets; the static strategy yields 2.27. The conclusions are not driven by overlap mechanics, though the static result remains marginal under either treatment.

### 6.3 The 6N exclusion

6N implied volatility in 2010 through 2013 is structurally anomalous (Section 3.6) and is excluded before 2014-01-01 in all results. In addition, a full-exclusion variant (static_ex_6N) is reported in Table 3 and is stronger than the all-roots static strategy, which is expected given that 6N carries no measurable premium even in its clean sample.

### 6.4 Stress-year analysis

2022 is the principal short-volatility stress year, with negative median VRP across all seven roots (from -0.12 for 6C to -1.69 for 6J). This is the period in which a short-volatility seller pays out the insurance they had been collecting, and it should be presented as an integral feature of the premium rather than an anomaly.

---

## 7. Limitations

1. All strategy results are payoff proxies (ex-post IV minus forward RV of selected positions), not executable P&L.
2. Transaction costs are excluded. Measurement of resting-quote bid-ask spreads from the statistics schema (stat_types 7 and 8) is preliminary and pending; no cost figure is claimed in this version. Given the static mean spread of 0.28 volatility points, plausible option bid-ask costs could consume much of the unconditional premium, while the conditional spread of 0.51 has more headroom. A rigorous cost analysis is required before any tradability claim.
3. Delta-hedging costs and slippage are not modelled; the proxy corresponds most closely to a vega-normalized delta-hedged position with frictionless hedging.
4. Margin and capital usage are not modelled, so no return-on-capital or Sharpe ratio is claimed.
5. Pre-2017 legacy contracts are American-style and are approximated with Black-76, biasing legacy IV (and hence pre-2017 VRP) slightly upward.
6. The risk-free rate is set to zero in this pass.
7. The panel is ATM-only; volatility smiles, 25-delta risk reversals, and butterflies are not constructed.
8. Event risk and macro announcements are not explicitly modelled.
9. Forward RV windows overlap; this is addressed with Newey-West and non-overlapping sampling but remains a structural feature of the design.
10. The headline conditional strategy is the best of twelve tested variants; its significance should be discounted for specification search, as discussed in Section 5.5.
11. 6N results carry a thin-market caveat throughout: roughly 78 percent of its daily cells have zero open interest even in the clean sample.

---

## 8. Future Work

1. Use actual DTE rather than target tenor for the realized-volatility horizon, and compare trading-day versus calendar-day annualization conventions (the stored return counts and spans permit both).
2. Add a SOFR or Treasury curve in place of r = 0.
3. Construct the full implied-volatility surface per root.
4. Compute 25-delta risk reversals and butterflies, enabling skew-premium studies.
5. Add macro regime filters: VIX, MOVE, DXY, rate differentials, CPI surprises, and FOMC dates.
6. Build a full transaction-cost model from the bid-ask statistics, including the liquidity-selection correction for days without resting quotes.
7. Convert the payoff proxy into a realistic delta-hedged short-option backtest with discrete hedging and costs.
8. Extend the framework to equity index, rates, energy, and metals options on futures.

---

## 9. Conclusion

This project constructs a cleaned CME G10 FX options on futures dataset spanning 2010 to 2026 and documents a persistent volatility risk premium. After correcting for the 2017 CME symbol migration, removing an anomalous legacy 6N volatility regime, and computing Black-76 implied volatility, implied volatility is found to exceed forward realized volatility across most roots and tenors, with the strongest premium in JPY and essentially none in NZD.

A static short-volatility payoff proxy is positive but only marginally significant after Newey-West correction. Conditioning on high implied volatility through a leak-free cross-sectional selection rule nearly doubles the mean payoff proxy and strengthens robust significance, with monotone attenuation across ranks; time-series threshold rules do not add value once look-ahead is removed. The premium is not riskless: its payoff distribution is left-skewed in every variant, and 2022 delivers broad losses to volatility sellers across all seven currencies. The premium is best understood as insurance compensation, collected steadily and repaid in concentrated stress regimes. The practical value of harvesting it therefore depends on transaction costs, risk management, and macro regime awareness, all of which are identified as the natural next stage of this research.

---

## Appendix

- A1. CME symbol migration mapping (Section 3.3 table, plus raw symbol examples)
- A2. Data cleaning and join rules (dedup keys, join keys, validation counts; see also diagnostics/reproduction_scorecard.csv)
- A3. Black-76 formulas and implementation notes (scripts/07_black76_iv.py)
- A4. IV solver validation (status counts, below-intrinsic handling, 6N diagnostic)
- A5. VRP construction details (per-instrument forward RV, trading-day annualization, rv_status flags; scripts/10_vrp.py)
- A6. Strategy definitions (all twelve variants; z-score: trailing 252-observation rolling mean and standard deviation ending at t-1, minimum 126 observations; scripts/12_strategy_proxy.py)
- A7. Robust statistics methodology (NW lags 5/21/63; 21-offset non-overlapping scheme; scripts/13_robust_stats.py)
- A8. Additional charts (clean_v3/vrp_v3/charts_step14)
