import os

import pandas as pd
import pytest

pytestmark = pytest.mark.skipif("FX_VRP_WORK" not in os.environ,
                                reason="FX_VRP_WORK is not set")


def vrp_path(*parts):
    return os.path.join(os.environ["FX_VRP_WORK"], "clean_v3", "vrp_v3", *parts)


def test_daily_rows():
    d = pd.read_parquet(vrp_path("daily_panel_step11", "daily_vrp_panel_v3.parquet"))
    assert len(d) == 70714


def test_published_numbers():
    rob = pd.read_csv(vrp_path("robust_stats_step13", "robust_strategy_summary_v3.csv"),
                      index_col=0)
    static = rob.loc["static_all_roots_all_tenors"]
    assert static["mean"] == pytest.approx(0.2766)
    assert static["t_nw63"] == pytest.approx(1.7906)
    top1 = rob.loc["xs_top1_iv_z_by_date_tenor"]
    assert top1["mean"] == pytest.approx(0.5126)
    assert top1["t_nw63"] == pytest.approx(2.4139)
    assert top1["t_nonoverlap21"] == pytest.approx(2.7073)
