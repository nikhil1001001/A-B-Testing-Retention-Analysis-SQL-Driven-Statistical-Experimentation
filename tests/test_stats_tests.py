import numpy as np
import pandas as pd
import pytest
from src.stats_tests import (
    check_srm,
    test_retention as run_test_retention,
    test_engagement as run_test_engagement,
    retrospective_power
)


def test_srm_balanced_and_unbalanced():
    """Verify SRM test on known perfectly balanced and severely unbalanced samples."""
    # Balanced 50/50: 10,000 vs 10,000
    res_balanced = check_srm(10000, 10000)
    assert res_balanced["chi2_stat"] == 0.0
    assert res_balanced["p_value"] == 1.0
    assert res_balanced["srm_detected"] is False

    # Broken split: 4,000 vs 6,000 (Expected 5,000 each)
    res_broken = check_srm(4000, 6000)
    assert res_broken["chi2_stat"] == 400.0
    assert res_broken["p_value"] < 1e-20
    assert res_broken["srm_detected"] is True


def test_retention_identical_proportions():
    """Verify Chi-Square and Z-test on perfectly identical synthetic retention."""
    n = 1000
    df_identical = pd.DataFrame({
        "version": ["gate_30"] * n + ["gate_40"] * n,
        "retention_7": [True] * 200 + [False] * 800 + [True] * 200 + [False] * 800,
        "sum_gamerounds": [10] * (2 * n)
    })
    res = run_test_retention(df_identical, "retention_7")
    assert res["rate_gate30"] == 0.20
    assert res["rate_gate40"] == 0.20
    assert res["absolute_difference"] == 0.0
    assert res["chi2_p_value"] == 1.0
    assert res["z_p_value"] == 1.0
    assert res["tests_agree"] is True


def test_retention_significant_difference():
    """Verify Chi-Square and Z-test detect known significant difference."""
    n = 5000
    df_diff = pd.DataFrame({
        "version": ["gate_30"] * n + ["gate_40"] * n,
        "retention_7": [True] * 1250 + [False] * 3750 + [True] * 1000 + [False] * 4000,  # 25% vs 20%
        "sum_gamerounds": [15] * (2 * n)
    })
    res = run_test_retention(df_diff, "retention_7")
    assert res["rate_gate30"] == 0.25
    assert res["rate_gate40"] == 0.20
    assert res["chi2_p_value"] < 1e-5
    assert res["z_p_value"] < 1e-5
    assert res["tests_agree"] is True


def test_engagement_mann_whitney():
    """Verify Mann-Whitney U test on synthetic shifted distributions."""
    rng = np.random.default_rng(42)
    rounds_a = rng.exponential(scale=10, size=500)
    rounds_b = rng.exponential(scale=30, size=500)

    df_eng = pd.DataFrame({
        "version": ["gate_30"] * 500 + ["gate_40"] * 500,
        "sum_gamerounds": np.concatenate([rounds_a, rounds_b]),
        "retention_7": [True] * 1000
    })
    res = run_test_engagement(df_eng)
    assert res["significant_at_05"] is True
    assert res["p_value"] < 1e-10


def test_retrospective_power_calculation():
    """Verify power calculation yields valid bounds and correct MDE scaling."""
    power_res = retrospective_power(p1=0.20, p2=0.18, n_per_group=40000, alpha=0.05)
    assert 0.0 < power_res["achieved_power"] <= 1.0
    assert power_res["target_power"] == 0.80
    assert power_res["approx_mde_abs_percentage_points"] > 0.0
