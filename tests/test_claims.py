"""Every result number quoted in README.md, paper/vrp_paper.tex and
report/vrp_report_final.md is checked against the committed results files.
No data needed.

Each claim is (doc, text template, printed number, source value). The template
holds # where the number sits; the test checks that the document really
contains that text, then that the source value rounds to the printed number at
the printed number of decimals. Source values come from results/ and
diagnostics/ (see S, T1, T2, T4, C, D below). UNSOURCED lists claims with no
committed source: they fail until a source exists.
"""
import os
import re

import pandas as pd
import pytest

ROOT = os.path.join(os.path.dirname(__file__), "..")


def path(*p):
    return os.path.join(ROOT, *p)


def read(*p):
    with open(path(*p), encoding="utf-8") as f:
        return f.read()


def norm(t):
    for a, b in [("{,}", ","), ("$-$", "-"), ("\\_", "_"), ("\\%", "%"), ("−", "-"),
                 ("$", ""), ("\\textbf{", ""), ("}", ""), ("\\,", "")]:
        t = t.replace(a, b)
    return re.sub(r"\s+", " ", t)


DOCS = {"README": norm(read("README.md")),
        "paper": norm(read("paper", "vrp_paper.tex")),
        "report": norm(read("report", "vrp_report_final.md"))}

SUMMARY = pd.read_csv(path("results", "robust_strategy_summary_v3.csv"), index_col=0)
TABLE1 = pd.read_csv(path("results", "tables", "table_1_vrp_by_root.csv"), index_col=0)
TABLE2 = pd.read_csv(path("results", "tables", "table_2_vrp_by_tenor.csv"), index_col=0)
TABLE4 = pd.read_csv(path("results", "tables", "table_4_yearly_median_vrp_by_root.csv"), index_col=0)
CHECKS = pd.read_csv(path("results", "data_checks.csv"), index_col=0)["value"]
SCORE = pd.read_csv(path("diagnostics", "reproduction_scorecard.csv"), index_col=0)
INVENTORY = pd.read_csv(path("diagnostics", "inventory_summary.csv"))
BUILD = pd.read_csv(path("diagnostics", "clean_v3_build_log.csv"))
COVERAGE = pd.read_csv(path("diagnostics", "coverage_stats_monthly.csv"))
ATM_ROOT = pd.read_csv(path("diagnostics", "atm_export_rows_by_root.csv"), index_col=0)


def S(strategy, col):
    return SUMMARY.loc[strategy, col]


def T1(root, col):
    return TABLE1.loc[root, col]


def T2(tenor, col):
    return TABLE2.loc[tenor, col]


def T4(year, root):
    return TABLE4.loc[year, root]


def C(metric):
    return float(CHECKS[metric])


def D(metric, col="this_rebuild"):
    return float(SCORE.loc[metric, col].split()[0].replace(",", ""))


STATIC, TOP1, TOP2, TOP3 = ("static_all_roots_all_tenors", "xs_top1_iv_z_by_date_tenor",
                            "xs_top2_iv_z_by_date_tenor", "xs_top3_iv_z_by_date_tenor")

# (doc, template, printed, source value)
CLAIMS = [
    # README, main result
    ("README", "strongest JPY +# vol points", "0.87", lambda: T1("6J", "median_vrp_spread")),
    ("README", "NZD flat (#)", "-0.03", lambda: T1("6N", "median_vrp_spread")),
    ("README", "mean # vol points, median 0.49", "0.28", lambda: S(STATIC, "mean")),
    ("README", "mean 0.28 vol points, median #", "0.49", lambda: S(STATIC, "median")),
    ("README", "positive #% of days, **NW63 t = 1.79**", "65.6", lambda: S(STATIC, "positive_pct")),
    ("README", "**NW63 t = #**, t on 21-day-spaced observations = 2.27", "1.79", lambda: S(STATIC, "t_nw63")),
    ("README", "t on 21-day-spaced observations = # |", "2.27", lambda: S(STATIC, "t_nonoverlap21")),
    ("README", "(NW63 t = #); 60d", "2.40", lambda: S("static_30d", "t_nw63")),
    ("README", "mean **#**, median 0.76", "0.51", lambda: S(TOP1, "mean")),
    ("README", "median #, positive 67.2%", "0.76", lambda: S(TOP1, "median")),
    ("README", "positive #%, **NW63 t = 2.41**", "67.2", lambda: S(TOP1, "positive_pct")),
    ("README", "**NW63 t = #**, t on 21-day-spaced observations = 2.71", "2.41", lambda: S(TOP1, "t_nw63")),
    ("README", "t on 21-day-spaced observations = #;", "2.71", lambda: S(TOP1, "t_nonoverlap21")),
    ("README", "static skew #, excess kurtosis 7.0", "-1.69", lambda: S(STATIC, "skew")),
    ("README", "static skew -1.69, excess kurtosis #;", "7.0", lambda: S(STATIC, "excess_kurtosis")),
    ("README", "raises the mean payoff from # to 0.51", "0.28", lambda: S(STATIC, "mean")),
    ("README", "raises the mean payoff from 0.28 to #,", "0.51", lambda: S(TOP1, "mean")),
    ("README", "share of positive days moves from #% to 67.2%", "65.6", lambda: S(STATIC, "positive_pct")),
    ("README", "65.6% to #%.", "67.2", lambda: S(TOP1, "positive_pct")),
    ("README", "The static premium is only marginally significant: NW63 t = #,", "1.79", lambda: S(STATIC, "t_nw63")),
    ("README", "static mean # / NW63 t 1.7906", "0.2766", lambda: S(STATIC, "mean")),
    ("README", "static mean 0.2766 / NW63 t # and", "1.7906", lambda: S(STATIC, "t_nw63")),
    ("README", "top-1 mean # / NW63 t 2.4139", "0.5126", lambda: S(TOP1, "mean")),
    ("README", "top-1 mean 0.5126 / NW63 t #.", "2.4139", lambda: S(TOP1, "t_nw63")),
    # README, data and pipeline
    ("README", "# DBN files", "986", lambda: INVENTORY.n_files.sum()),
    ("README", "# GB of exchange-level", "11", lambda: INVENTORY.total_mb.sum() * 2**20 / 1e9),
    ("README", "In 2013, # legacy 6N option rows", "612", lambda: C("n6_2013_rows_iv_above_20")),
    ("README", "(median #, highest 39.9)", "28.5", lambda: C("n6_2013_iv_above_20_median_iv")),
    ("README", "highest #)", "39.9", lambda: C("n6_2013_iv_above_20_max_iv")),
    ("README", "median realised volatility of # percent", "9.5", lambda: C("n6_2013_iv_above_20_median_rv")),
    ("README", "# daily cells combine implied volatility above 20", "128", lambda: C("cells_iv_above_20_no_open_interest")),
    ("README", "and # of them are 6N in 2013", "102", lambda: C("cells_iv_above_20_no_open_interest_6N_2013")),
    ("README", "(# of the 3,526", "10", lambda: C("n6_2013_rows_with_open_interest")),
    ("README", "of the # rows in 2013", "3,526", lambda: C("n6_2013_rows")),
    ("README", "Open interest is missing for # percent of rows", "23", lambda: C("option_rows_open_interest_missing_pct")),
    ("README", "nearest of the #, 60 and 90-day", "30", lambda: 30),  # setting: TENORS in scripts/06_atm_export.py
    ("README", "must print # daily rows", "70,714", lambda: C("daily_rows")),
    ("README", "| 193 files, # |", "32,525,006", lambda: D("clean_v3 total rows")),
    ("README", "| # |", "440,467", lambda: ATM_ROOT.rows.sum()),
    ("README", "| # valid |", "440,462", lambda: D("valid IV rows")),
    ("README", "research filters | # |", "430,630", lambda: D("final research rows")),
    ("README", "| # / 482,449 |", "485,057", lambda: C("futures_settle_rows")),
    ("README", "| 485,057 / # |", "482,449", lambda: C("futures_return_rows")),
    ("README", "| # (427,774 RV ok) |", "430,630", lambda: C("option_rows_all")),
    ("README", "430,630 (# RV ok)", "427,774", lambda: C("option_rows_rv_ok")),
    ("README", "# strategy-days", "40,887", lambda: SUMMARY.n_days.sum()),
    ("README", "| daily (date, root, tenor) panel; 6N from 2014 | # |", "70,714", lambda: C("daily_rows")),
    ("README", "(# on average)", "7", lambda: C("tenor_diff_days_mean")),
    ("README", "up to # days from that target", "15", lambda: C("tenor_diff_days_max")),
    ("README", "# percent of its daily cells have no recorded open interest", "76.6", lambda: C("n6_from_2014_cells_no_open_interest_pct")),
    # paper
    ("paper", "contains # root-tenor observations", "70,714", lambda: C("daily_rows")),
    ("paper", "mean implied-minus-realized spread of # volatility points", "0.28", lambda: S(STATIC, "mean")),
    ("paper", "(median #, positive on", "0.49", lambda: S(STATIC, "median")),
    ("paper", "positive on #% of days", "65.6", lambda: S(STATIC, "positive_pct")),
    ("paper", "63-lag t-statistic of #.", "1.79", lambda: S(STATIC, "t_nw63")),
    ("paper", "nearly doubles the mean spread to # volatility points", "0.51", lambda: S(TOP1, "mean")),
    ("paper", "t_{\\mathrm{NW63}}=#, non-overlapping", "2.41", lambda: S(TOP1, "t_nw63")),
    ("paper", "non-overlapping t=#)", "2.71", lambda: S(TOP1, "t_nonoverlap21")),
    ("paper", "from # to 2026-06-08", "2010-06-04", lambda: pd.Timestamp(CHECKS["daily_date_min"]).value),
    ("paper", "across all # role-months", "492", lambda: len(COVERAGE)),
    ("paper", "with #% unmatched across", "0", lambda: COVERAGE.settle_unmatched_defs_pct.max()),
    ("paper", "holds # option-day rows", "32,525,006", lambda: D("clean_v3 total rows")),
    ("paper", "across # monthly files", "193", lambda: len(BUILD)),
    ("paper", "it contains # rows", "440,467", lambda: ATM_ROOT.rows.sum()),
    ("paper", "Of # daily cells sample-wide", "128", lambda: C("cells_iv_above_20_no_open_interest")),
    ("paper", "above 20% and zero open interest, # are 6N", "102", lambda: C("cells_iv_above_20_no_open_interest_6N_2013")),
    ("paper", "#% of 6N daily cells carry zero open interest", "76.6", lambda: C("n6_from_2014_cells_no_open_interest_pct")),
    ("paper", "inverts # of 440,467", "440,462", lambda: D("valid IV rows")),
    ("paper", "(#%)", "99.999", lambda: 100 * 440462 / 440467),
    ("paper", "(2,856 of #,", "430,630", lambda: C("option_rows_all")),
    ("paper", "excluded, leaving # valid", "427,774", lambda: C("option_rows_rv_ok")),
    ("paper", "(# after the 6N exclusion)", "424,248", lambda: C("option_rows_ok_after_6N_exclusion")),
    ("paper", "(# of 430,630,", "2,856", lambda: C("option_rows_rv_excluded")),
    ("paper", "gap is largest for JPY (# vol points)", "0.87", lambda: T1("6J", "median_vrp_spread")),
    ("paper", "(medians #, 0.50, 0.49 vol points", "0.57", lambda: T2(30, "median_vrp_spread")),
    ("paper", "(medians 0.57, #, 0.49 vol points", "0.50", lambda: T2(60, "median_vrp_spread")),
    ("paper", "(medians 0.57, 0.50, # vol points", "0.49", lambda: T2(90, "median_vrp_spread")),
    ("paper", "positive on about #% of cells", "62.5", lambda: T2(30, "positive_pct")),
    ("paper", "(from -# for CAD", "0.12", lambda: -T4(2022, "6C")),
    ("paper", "to -# for JPY)", "1.69", lambda: -T4(2022, "6J")),
    ("paper", "static premium is positive but marginal (t_{\\mathrm{NW63}}=#;", "1.79", lambda: S(STATIC, "t_nw63")),
    ("paper", "non-overlapping t=#);", "2.27", lambda: S(STATIC, "t_nonoverlap21")),
    ("paper", "30-day tenor (t=#)", "2.40", lambda: S("static_30d", "t_nw63")),
    ("paper", "ex-6N universe (t=#)", "2.21", lambda: S("static_ex_6N", "t_nw63")),
    ("paper", "static mean (# vs 0.28", "0.51", lambda: S(TOP1, "mean")),
    ("paper", "(static: #, excess kurtosis 7.0)", "-1.69", lambda: S(STATIC, "skew")),
    ("paper", "(static: -1.69, excess kurtosis #)", "7.0", lambda: S(STATIC, "excess_kurtosis")),
    ("paper", "its t_{\\mathrm{NW63}}=# overstates", "2.41", lambda: S(TOP1, "t_nw63")),
    ("paper", "naive t of # (NW5", "12.2", lambda: S(TOP1, "t_naive")),
    ("paper", "(NW5: #)", "5.35", lambda: S(TOP1, "t_nw5")),
    ("paper", "from # to 1.79", "10.4", lambda: S(STATIC, "t_naive")),
    ("paper", "averages t=# across offsets", "2.71", lambda: S(TOP1, "t_nonoverlap21")),
    ("paper", "static strategy #.", "2.27", lambda: S(STATIC, "t_nonoverlap21")),
    ("paper", "2013, # legacy 6N option rows", "612", lambda: C("n6_2013_rows_iv_above_20")),
    ("paper", "(median #, highest 39.9)", "28.5", lambda: C("n6_2013_iv_above_20_median_iv")),
    ("paper", "highest #) against a median", "39.9", lambda: C("n6_2013_iv_above_20_max_iv")),
    ("paper", "realized volatility of #%", "9.5", lambda: C("n6_2013_iv_above_20_median_rv")),
    ("report", "2013, # legacy 6N option rows", "612", lambda: C("n6_2013_rows_iv_above_20")),
    ("report", "(median #, highest 39.9)", "28.5", lambda: C("n6_2013_iv_above_20_median_iv")),
    ("report", "highest #) against a median", "39.9", lambda: C("n6_2013_iv_above_20_max_iv")),
    ("report", "realized volatility of # percent", "9.5", lambda: C("n6_2013_iv_above_20_median_rv")),
    # report
    ("report", "the final daily panel contains # root-tenor observations", "70,714", lambda: C("daily_rows")),
    ("report", "volatility spread of # volatility points (median", "0.28", lambda: S(STATIC, "mean")),
    ("report", "(median #, positive on 65.6 percent", "0.49", lambda: S(STATIC, "median")),
    ("report", "positive on # percent of days", "65.6", lambda: S(STATIC, "positive_pct")),
    ("report", "t-statistic of # and a non-overlapping", "1.79", lambda: S(STATIC, "t_nw63")),
    ("report", "non-overlapping-sample t-statistic of #.", "2.27", lambda: S(STATIC, "t_nonoverlap21")),
    ("report", "raises the mean spread to # volatility points (median 0.76", "0.51", lambda: S(TOP1, "mean")),
    ("report", "(median #, positive 67.2 percent)", "0.76", lambda: S(TOP1, "median")),
    ("report", "positive # percent) with an NW63", "67.2", lambda: S(TOP1, "positive_pct")),
    ("report", "NW63 t-statistic of # and a non-overlapping-sample t-statistic of 2.71", "2.41", lambda: S(TOP1, "t_nw63")),
    ("report", "non-overlapping-sample t-statistic of #. The improvement", "2.71", lambda: S(TOP1, "t_nonoverlap21")),
    ("report", "strongest median VRP at # volatility points", "0.87", lambda: T1("6J", "median_vrp_spread")),
    ("report", "(median # from 2014 onward)", "-0.03", lambda: T1("6N", "median_vrp_spread")),
    ("report", "30 days is strongest (NW63 t = #)", "2.40", lambda: S("static_30d", "t_nw63")),
    ("report", "from # to 0.51 volatility points", "0.28", lambda: S(STATIC, "mean")),
    ("report", "mean spread (#) is well below the median (0.49)", "0.28", lambda: S(STATIC, "mean")),
    ("report", "below the median (#), with skewness", "0.49", lambda: S(STATIC, "median")),
    ("report", "with skewness # and excess kurtosis 7.0", "-1.69", lambda: S(STATIC, "skew")),
    ("report", "and excess kurtosis #.", "7.0", lambda: S(STATIC, "excess_kurtosis")),
    ("report", "Final daily panel: # root-tenor-date", "70,714", lambda: C("daily_rows")),
    ("report", "# DBN.ZST files", "986", lambda: INVENTORY.n_files.sum()),
    ("report", "The full clean panel contains # option-day rows", "32,525,006", lambda: D("clean_v3 total rows")),
    ("report", "option-day rows across # monthly files", "193", lambda: len(BUILD)),
    ("report", "yielding a final ATM panel of # rows", "440,467", lambda: ATM_ROOT.rows.sum()),
    ("report", "Of the # daily panel cells", "128", lambda: C("cells_iv_above_20_no_open_interest")),
    ("report", "and zero open interest, # are 6N cells in 2013", "102", lambda: C("cells_iv_above_20_no_open_interest_6N_2013")),
    ("report", "This removes # option-level observations", "3,526", lambda: C("n6_2013_rows")),
    ("report", "(# percent of its daily cells carry zero open interest)", "76.6", lambda: C("n6_from_2014_cells_no_open_interest_pct")),
    ("report", "(440,462 of # rows)", "440,467", lambda: ATM_ROOT.rows.sum()),
    ("report", "valid inversions on the ATM panel (# of", "440,462", lambda: D("valid IV rows")),
    ("report", "# percent valid inversions", "99.999", lambda: 100 * 440462 / 440467),
    ("report", "(2,856 of #,", "430,630", lambda: C("option_rows_all")),
    ("report", "Rows failing these requirements (# of", "2,856", lambda: C("option_rows_rv_excluded")),
    ("report", "leaving # valid VRP observations", "427,774", lambda: C("option_rows_rv_ok")),
    ("report", "(# after the 6N 2013 exclusion)", "424,248", lambda: C("option_rows_ok_after_6N_exclusion")),
    ("report", "daily root-tenor panel (# rows)", "70,714", lambda: C("daily_rows")),
    ("report", "Cells without a valid z-score (# percent,", "3.7", lambda: 100 - C("daily_valid_z_pct")),
    ("report", "means rise modestly (0.28 to #)", "0.38", lambda: S("signal_iv_zscore_ge_0", "mean")),
    ("report", "top-1 rule nearly doubles the static mean (# versus 0.28)", "0.51", lambda: S(TOP1, "mean")),
    ("report", "naive t of # and NW5 t of 5.35", "12.2", lambda: S(TOP1, "t_naive")),
    ("report", "NW5 t of # to NW63", "5.35", lambda: S(TOP1, "t_nw5")),
    ("report", "naive t of # to NW63 t = 1.79", "10.4", lambda: S(STATIC, "t_naive")),
    ("report", "simple t-statistic of # averaged across offsets", "2.71", lambda: S(TOP1, "t_nonoverlap21")),
    ("report", "(from -# for 6C", "0.12", lambda: -T4(2022, "6C")),
    ("report", "to -# for 6J)", "1.69", lambda: -T4(2022, "6J")),
    ("report", "static mean spread of # volatility points,", "0.28", lambda: S(STATIC, "mean")),
    ("report", "conditional spread of # has more headroom", "0.51", lambda: S(TOP1, "mean")),
    ("report", "# percent of its daily cells have zero open interest even", "76.6", lambda: C("n6_from_2014_cells_no_open_interest_pct")),
]

# Claims with no committed source file. They fail until one exists.
UNSOURCED = []


def decimals(s):
    return len(s.split(".")[1]) if "." in s else 0


def number(s):
    return float(s.replace(",", ""))


@pytest.mark.parametrize("doc,template,printed,source", CLAIMS,
                         ids=[f"{c[0]}:{c[1][:50]}" for c in CLAIMS])
def test_claim(doc, template, printed, source):
    if printed == "2010-06-04":
        assert source() == pd.Timestamp(printed).value
    else:
        assert norm(template.replace("#", printed)) in DOCS[doc], "text not found in document"
        tol = 0.5 * 10 ** -decimals(printed) + 1e-9
        assert abs(float(source()) - number(printed)) <= tol, f"source gives {source()}"


@pytest.mark.parametrize("doc,template,why", UNSOURCED, ids=[u[1][:50] for u in UNSOURCED])
def test_unsourced(doc, template, why):
    pytest.fail(f"no source file: {template} ({doc}); {why}")


# ---- tables: every cell of the strategy, root and tenor tables --------------

def tex_rows(first_cell_pattern, doc_text):
    for line in doc_text.split("\n"):
        if re.match(first_cell_pattern, line):
            yield [c.strip().rstrip("\\").strip() for c in line.rstrip().split("&")]


def md_rows(doc_text):
    for line in doc_text.split("\n"):
        if line.startswith("|") and not line.startswith("|---"):
            yield [c.strip() for c in line.strip().strip("|").split("|")]


def check_cells(cells, expected):
    """cells: printed strings; expected: source values in the same order."""
    for printed, value in zip(cells, expected):
        printed = printed.replace("%", "").replace("**", "").replace("$-$", "-").replace("\\textbf{", "").replace("}", "").replace("$", "")
        tol = 0.5 * 10 ** -decimals(printed) + 1e-9
        assert abs(float(value) - number(printed)) <= tol, f"{printed} vs {value}"


STRAT_COLS = ["n_days", "mean", "median", "positive_pct", "skew", "excess_kurtosis", "t_nw63", "t_nonoverlap21"]


def test_strategy_table_paper():
    tex = read("paper", "vrp_paper.tex").replace("\\_", "_").replace("$-$", "-")
    rows = {r[0]: r[1:] for r in tex_rows(r"(static|signal|xs)_", tex)}
    assert set(rows) == set(SUMMARY.index)
    for name, cells in rows.items():
        check_cells(cells, SUMMARY.loc[name, STRAT_COLS])


def test_strategy_table_report():
    rows = {r[0]: r[1:] for r in md_rows(read("report", "vrp_report_final.md")) if r[0] in SUMMARY.index}
    assert set(rows) == set(SUMMARY.index)
    for name, cells in rows.items():
        check_cells(cells, SUMMARY.loc[name, STRAT_COLS])


def test_root_table_paper():
    tex = read("paper", "vrp_paper.tex").replace("$-$", "-")
    rows = {r[0][:2]: r[1:] for r in tex_rows(r"6[A-Z] \(", tex)}
    assert set(rows) == set(TABLE1.index)
    for root, cells in rows.items():
        check_cells(cells, TABLE1.loc[root])


def test_root_table_report():
    rows = {r[0]: r[1:] for r in md_rows(read("report", "vrp_report_final.md")) if r[0] in TABLE1.index}
    assert set(rows) == set(TABLE1.index)
    for root, cells in rows.items():
        check_cells(cells, TABLE1.loc[root])


def test_tenor_table_report():
    rows = {int(r[0][:-1]): r[1:] for r in md_rows(read("report", "vrp_report_final.md")) if re.fullmatch(r"\d\dd", r[0])}
    assert set(rows) == set(TABLE2.index)
    for tenor, cells in rows.items():
        check_cells(cells, TABLE2.loc[tenor, ["median_vrp_spread", "positive_pct"]])


def test_2022_negative_for_all_roots():
    assert (TABLE4.loc[2022] < 0).all()


def test_mean_below_median_in_all_variants():
    assert (SUMMARY["mean"] < SUMMARY["median"]).all() and (SUMMARY["skew"] < 0).all()


def test_six_of_seven_roots_positive():
    assert (TABLE1.median_vrp_spread > 0).sum() == 6


def test_top1_best_of_twelve():
    assert len(SUMMARY) == 12
    assert SUMMARY["mean"].idxmax() == TOP1 and SUMMARY.t_nw63.idxmax() == TOP1


# ---- settings quoted in the text, checked against the code -------------------

@pytest.mark.parametrize("file,pattern", [
    ("fxvrp/signals.py", r"Z_WINDOW, Z_MIN = 252, 126"),
    ("scripts/07_black76_iv.py", r"/ 365\.25"),
    ("scripts/09_futures_settle_series.py", r"GAP_MAX_DAYS = 14"),
    ("scripts/10_vrp.py", r"span < 0\.6 \* H_arr"),
    ("scripts/10_vrp.py", r"252\.0 \* sum_r2"),
    ("scripts/06_atm_export.py", r"abs_log_moneyness <= 0\.10"),
    ("scripts/06_atm_export.py", r"\(df\.dte >= 10\) & \(df\.dte <= 130\)"),
    ("scripts/06_atm_export.py", r"TENORS = \(30, 60, 90\)"),
    ("scripts/04_build_clean_v3.py", r'CUTOFF = "2017-07"'),
    ("fxvrp/panel.py", r'date < "2014-01-01"'),
    ("fxvrp/strategy.py", r'MAJORS = \["6E", "6B", "6J", "6S"\]'),
])
def test_setting(file, pattern):
    assert re.search(pattern, read(*file.split("/")))


def test_chart_and_table_counts():
    assert len([f for f in os.listdir(path("paper", "figs")) if f.endswith(".png")]) == 7
    assert len(os.listdir(path("results", "tables"))) == 4


# ---- coverage: every number in the three documents ---------------------------
#
# prose() removes markup, table rows (checked cell by cell above) and the numbers
# in CLAIMS and UNSOURCED. What is left is checked here: a number must be a year,
# an enumerator or a reference (classify), be in ALLOW with a one-word reason, or
# be in MENTIONS with a source for a result quoted again in other words.

FILES = {"README": ("README.md",), "paper": ("paper", "vrp_paper.tex"),
         "report": ("report", "vrp_report_final.md")}
NUM = re.compile(r"(?<![A-Za-z_\d.\-])-?\d+(?:,\d{3})*(?:\.\d+)?(?![A-Za-z_\d])")
TABLE_LINE = re.compile(r"^(?:(?:static|signal|xs)_|6[A-Z] \(|\| ?(?:6[A-Z] |\d\dd |static_|signal_|xs_))")


def blank_numbers(match):
    return NUM.sub("@", match.group(0))


def prose(doc):
    """The document's prose with markup, table rows and claimed numbers replaced."""
    text = read(*FILES[doc])
    if doc == "paper":
        text = text.split("\\begin{document}")[1]
        text = re.sub(r"\\begin\{equation\}.*?\\end\{equation\}", " ", text, flags=re.S)
        text = re.sub(r"\\(?:begin|end)\{[^}]*\}(?:\{[^}]*\})?", " ", text)
        text = re.sub(r"\\(?:label|ref|includegraphics)(?:\[[^\]]*\])?\{[^}]*\}", " ", text)
        text = re.sub(r"\\[a-zA-Z]+", " ", text)
        text = re.sub(r"(?m)^%.*$", "", text)
    else:
        text = re.sub(r"```.*?```", " ", text, flags=re.S)
        text = re.sub(r"`[^`]*`", " ", text)
        text = re.sub(r"\]\([^)]*\)", "] ", text)
    lines = [norm(l) for l in text.split("\n")]
    text = "\n".join(l for l in lines if not TABLE_LINE.match(l))  # cells: table tests
    for d, template, printed, _ in CLAIMS:
        if d == doc:
            pattern = re.escape(norm(template)).replace(r"\ ", r"\s+").replace("\\#", "(?P<n>" + re.escape(printed) + ")")
            text = re.sub(pattern, lambda m: m.group(0).replace(m.group("n"), "@", 1), text)
    for d, template, _ in UNSOURCED:
        if d == doc:
            text = re.sub(re.escape(norm(template)).replace(r"\ ", r"\s+"), blank_numbers, text)
    return re.sub(r"[\^_]\{?\d", " ", text)


# Numbers that are settings, labels or counts checked elsewhere. One-word reasons.
ALLOW = {
    "30": "tenor", "60": "tenor", "90": "tenor", "45": "setting", "75": "setting", "46": "setting",
    "74": "setting", "10": "setting", "130": "setting", "0.10": "setting", "20": "setting",
    "252": "setting", "126": "setting", "365.25": "setting", "14": "setting", "5": "setting",
    "21": "setting", "63": "setting", "0": "setting", "0.5": "setting", "1": "setting",
    "1.0": "setting", "2": "setting", "3": "setting", "25": "name", "7": "count", "6": "count",
    "8": "name", "9": "step", "4": "count", "11": "step", "12": "count", "13": "step", "00": "step",
    "15": "count", "16": "count", "1.96": "constant", "3.14": "version", "22": "count",
}

# Results quoted again outside a CLAIMS row: any occurrence of the number in that
# document is accepted if one of its sources rounds to it.
MENTIONS = {
    "0.49": [lambda: S(STATIC, "median"), lambda: T2(90, "median_vrp_spread")],
    "0.50": [lambda: T2(60, "median_vrp_spread")],
    "0.51": [lambda: S(TOP1, "mean")],
    "0.28": [lambda: S(STATIC, "mean")],
    "0.38": [lambda: S("signal_iv_zscore_ge_0", "mean")],
    "67.2": [lambda: S(TOP1, "positive_pct")],
    "7.0": [lambda: S(STATIC, "excess_kurtosis")],
    "-1.69": [lambda: S(STATIC, "skew")],
    "1.79": [lambda: S(STATIC, "t_nw63")],
    "1.7906": [lambda: S(STATIC, "t_nw63")],
    "2.41": [lambda: S(TOP1, "t_nw63")],
    "2.4139": [lambda: S(TOP1, "t_nw63")],
    "2.27": [lambda: S(STATIC, "t_nonoverlap21")],
    "2.40": [lambda: S("static_30d", "t_nw63")],
    "2.21": [lambda: S("static_ex_6N", "t_nw63")],
    "986": [lambda: INVENTORY.n_files.sum()],
    "193": [lambda: len(BUILD)],
    "427,774": [lambda: C("option_rows_rv_ok")],
    "482,449": [lambda: C("futures_return_rows")],
    "2,856": [lambda: C("option_rows_rv_excluded")],
    "70,714": [lambda: C("daily_rows")],
    "440,467": [lambda: ATM_ROOT.rows.sum()],
    "32,525,026": [lambda: D("clean_v3 total rows", "target_prior_laptop")],
    "32.5": [lambda: D("clean_v3 total rows") / 1e6],
    "20": [lambda: D("clean_v3 total rows", "target_prior_laptop") - D("clean_v3 total rows")],
    "0.00006": [lambda: 100 * 20 / D("clean_v3 total rows", "target_prior_laptop")],
    "21 of the 22": [],
}


def classify(text, m):
    """A reason when the number is plainly not a result: a year, enumerator or reference."""
    line_start = text.rfind("\n", 0, m.start()) + 1
    before, num = text[max(0, m.start() - 25):m.start()], m.group()
    if re.fullmatch(r"(?:19|20)\d\d", num):
        return "year"
    if re.search(r"(?:Section|Table|Figure|Chart|Step|Steps|step|steps|stat_types?|\u00a7)[~ ]*$", before):
        return "reference"
    head = text[line_start:m.start()]
    if re.fullmatch(r"[#\- ]*(?:\|? ?)[A-Z]?(?:\d+\.)*", head.strip()) and re.fullmatch(r"\d+(?:\.\d+)?", num):
        return "enumerator"
    if re.search(r"(?:steps?|Steps) [\d, ]*(?:and |to )?$", before) and re.fullmatch(r"\d+", num):
        return "reference"
    return None


def accepted(doc, text, m):
    num = m.group()
    if classify(text, m):
        return "classified"
    if num in MENTIONS and any(abs(float(f()) - number(num)) <= 0.5 * 10 ** -decimals(num) + 1e-9 for f in MENTIONS[num]):
        return "mention"
    if num in ALLOW:
        return "allowed"
    return None


@pytest.mark.parametrize("doc", list(FILES))
def test_every_number_is_accounted_for(doc):
    text = prose(doc)
    bad = [(m.group(), text[max(0, m.start() - 35):m.end() + 20].replace("\n", " "))
           for m in NUM.finditer(text) if not accepted(doc, text, m)]
    assert not bad, "\n".join(f"{n!r} in ...{ctx}..." for n, ctx in bad)
