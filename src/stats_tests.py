"""Statistical hypothesis testing and experiment integrity suite for Cookie Cats A/B Test.

This module implements:
1. Chi-Square Test of Independence & Two-Proportion Z-Test for retention metrics.
2. Non-parametric Mann-Whitney U Test for right-skewed engagement metrics.
3. Retrospective Statistical Power & Minimum Detectable Effect (MDE) calculations.
4. Sample Ratio Mismatch (SRM) goodness-of-fit validation.
"""

import os
import sys
from typing import Dict, Any, Tuple
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.proportion import proportions_ztest, proportion_effectsize
from statsmodels.stats.power import NormalIndPower

# Support both direct script execution and package imports
try:
    from src.data_prep import load_and_clean
except ModuleNotFoundError:
    from data_prep import load_and_clean


def check_srm(
    n_group_a: int,
    n_group_b: int,
    expected_ratio: Tuple[float, float] = (0.5, 0.5),
    alpha: float = 0.01
) -> Dict[str, Any]:
    """Perform a Sample Ratio Mismatch (SRM) goodness-of-fit test.

    Parameters
    ----------
    n_group_a : int
        Observed sample size in Group A (e.g. gate_30).
    n_group_b : int
        Observed sample size in Group B (e.g. gate_40).
    expected_ratio : Tuple[float, float], default (0.5, 0.5)
        Expected allocation proportions between Group A and Group B.
    alpha : float, default 0.01
        Significance threshold for flagging an SRM. A strict threshold (0.01)
        is standard in industry to avoid false alarms in sample allocation.

    Returns
    -------
    Dict[str, Any]
        Dictionary containing observed counts, expected counts, chi2 statistic,
        p-value, and SRM verdict.
    """
    total_n = n_group_a + n_group_b
    ratio_sum = sum(expected_ratio)
    expected_a = total_n * (expected_ratio[0] / ratio_sum)
    expected_b = total_n * (expected_ratio[1] / ratio_sum)

    observed = [n_group_a, n_group_b]
    expected = [expected_a, expected_b]

    chi2_stat, p_value = stats.chisquare(f_obs=observed, f_exp=expected)
    srm_detected = bool(p_value < alpha)

    result = {
        "test_name": "Sample Ratio Mismatch (SRM) Chi-Square Goodness of Fit",
        "n_group_a": n_group_a,
        "n_group_b": n_group_b,
        "expected_a": expected_a,
        "expected_b": expected_b,
        "chi2_stat": float(chi2_stat),
        "p_value": float(p_value),
        "alpha_threshold": alpha,
        "srm_detected": srm_detected,
        "verdict": (
            "SRM Detected (Potential Traffic Routing / Tracking Bias)"
            if srm_detected
            else "Passed (No Evidence of Sample Ratio Mismatch)"
        ),
    }
    return result


def test_retention(df: pd.DataFrame, metric: str = "retention_7") -> Dict[str, Any]:
    """Test differences in binary retention rates between gate_30 and gate_40.

    Executes both a Chi-Square test of independence and a two-proportion Z-test
    to cross-validate asymptotic agreement.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned Cookie Cats DataFrame.
    metric : str, default 'retention_7'
        Column name to test ('retention_1' or 'retention_7').

    Returns
    -------
    Dict[str, Any]
        Dictionary containing contingency table, retention rates, Chi-Square
        results, Two-Proportion Z-test results, and agreement verification.
    """
    if metric not in df.columns:
        raise ValueError(f"Metric {metric} not found in DataFrame columns.")

    # Contingency table: rows = version, columns = retained (False, True)
    contingency_table = pd.crosstab(df["version"], df[metric])
    
    # Extract counts
    n_gate30 = len(df[df["version"] == "gate_30"])
    n_gate40 = len(df[df["version"] == "gate_40"])
    
    retained_gate30 = int(df[df["version"] == "gate_30"][metric].sum())
    retained_gate40 = int(df[df["version"] == "gate_40"][metric].sum())

    p_gate30 = retained_gate30 / n_gate30
    p_gate40 = retained_gate40 / n_gate40
    diff = p_gate40 - p_gate30
    pct_lift = (diff / p_gate30) * 100

    # 1. Chi-Square Test of Independence (with Yates' continuity correction = False for 2x2 large sample)
    chi2_stat, chi2_p, dof, expected = stats.chi2_contingency(contingency_table, correction=False)

    # 2. Two-Proportion Z-Test (statsmodels)
    counts = np.array([retained_gate30, retained_gate40])
    nobs = np.array([n_gate30, n_gate40])
    z_stat, z_p = proportions_ztest(count=counts, nobs=nobs, alternative="two-sided")

    # Confirm asymptotic agreement (z^2 approx equal to chi2)
    stat_agreement = np.isclose(z_stat ** 2, chi2_stat, atol=1e-3)
    p_agreement = np.isclose(chi2_p, z_p, atol=1e-4)

    return {
        "metric": metric,
        "n_gate30": n_gate30,
        "retained_gate30": retained_gate30,
        "rate_gate30": float(p_gate30),
        "n_gate40": n_gate40,
        "retained_gate40": retained_gate40,
        "rate_gate40": float(p_gate40),
        "absolute_difference": float(diff),
        "relative_lift_pct": float(pct_lift),
        "chi2_stat": float(chi2_stat),
        "chi2_p_value": float(chi2_p),
        "chi2_dof": int(dof),
        "z_stat": float(z_stat),
        "z_p_value": float(z_p),
        "tests_agree": bool(stat_agreement and p_agreement),
    }


def test_engagement(df: pd.DataFrame) -> Dict[str, Any]:
    """Test difference in game rounds played using the Mann-Whitney U test.

    The Mann-Whitney U test is chosen because sum_gamerounds is heavily right-skewed
    (violating the normality assumption of Student's t-test). It evaluates whether
    the distribution of rounds in gate_30 is stochastically greater or smaller
    than in gate_40.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned Cookie Cats DataFrame.

    Returns
    -------
    Dict[str, Any]
        Dictionary with Mann-Whitney U statistic, p-value, and rank-sum summaries.
    """
    rounds_gate30 = df[df["version"] == "gate_30"]["sum_gamerounds"].values
    rounds_gate40 = df[df["version"] == "gate_40"]["sum_gamerounds"].values

    u_stat, p_value = stats.mannwhitneyu(
        rounds_gate30, rounds_gate40, alternative="two-sided"
    )

    return {
        "test_name": "Mann-Whitney U Test (Non-parametric Engagement Comparison)",
        "metric": "sum_gamerounds",
        "reason_chosen": (
            "sum_gamerounds is heavily right-skewed (Phase 1 EDA confirmed skewness > 4); "
            "the normality assumption required by Student's t-test is violated."
        ),
        "mean_gate30": float(np.mean(rounds_gate30)),
        "median_gate30": float(np.median(rounds_gate30)),
        "mean_gate40": float(np.mean(rounds_gate40)),
        "median_gate40": float(np.median(rounds_gate40)),
        "u_stat": float(u_stat),
        "p_value": float(p_value),
        "significant_at_05": bool(p_value < 0.05),
    }


test_retention.__test__ = False
test_engagement.__test__ = False


def retrospective_power(
    p1: float,
    p2: float,
    n_per_group: int,
    alpha: float = 0.05,
    target_power: float = 0.80
) -> Dict[str, Any]:
    """Calculate retrospective statistical power and Minimum Detectable Effect (MDE).

    Uses statsmodels NormalIndPower and Cohen's h proportion effect size.

    Parameters
    ----------
    p1 : float
        Baseline proportion (e.g. gate_30 retention rate).
    p2 : float
        Observed treatment proportion (e.g. gate_40 retention rate).
    n_per_group : int
        Sample size per experimental group.
    alpha : float, default 0.05
        Two-sided significance level.
    target_power : float, default 0.80
        Standard target power for MDE calculation.

    Returns
    -------
    Dict[str, Any]
        Dictionary with effect size h, achieved power, and MDE at target power.
    """
    effect_size = proportion_effectsize(p1, p2)
    power_analysis = NormalIndPower()

    # Post-hoc achieved power given observed effect size
    achieved_power = power_analysis.power(
        effect_size=abs(effect_size),
        nobs1=n_per_group,
        alpha=alpha,
        ratio=1.0,
        alternative="two-sided"
    )

    # Minimum Detectable Effect size (Cohen's h) at target power (e.g. 80%)
    mde_effect_size = power_analysis.solve_power(
        effect_size=None,
        nobs1=n_per_group,
        alpha=alpha,
        power=target_power,
        ratio=1.0,
        alternative="two-sided"
    )

    # Convert MDE effect size back to approximate absolute percentage point change
    # Using h = 2 * (arcsin(sqrt(p2)) - arcsin(sqrt(p1))) approximation:
    # delta_p ~ mde_effect_size * sqrt(p1 * (1 - p1))
    approx_mde_abs = mde_effect_size * np.sqrt(p1 * (1 - p1))

    return {
        "p_control": float(p1),
        "p_treatment": float(p2),
        "n_per_group": int(n_per_group),
        "alpha": float(alpha),
        "observed_effect_size_h": float(effect_size),
        "achieved_power": float(achieved_power),
        "target_power": float(target_power),
        "mde_effect_size_h": float(mde_effect_size),
        "approx_mde_abs_percentage_points": float(approx_mde_abs * 100),
    }


def run_full_statistical_pipeline(
    df: pd.DataFrame = None,
    output_report_path: str = "outputs/stats_report.md"
) -> Dict[str, Any]:
    """Execute all statistical hypothesis tests, SRM check, and power analysis.

    Writes the formal statistical report to output_report_path.

    Parameters
    ----------
    df : pd.DataFrame, optional
        Cleaned DataFrame. If None, loaded via load_and_clean().
    output_report_path : str, default 'outputs/stats_report.md'
        Path to output markdown report.

    Returns
    -------
    Dict[str, Any]
        Dictionary holding all test result dictionaries.
    """
    if df is None:
        df = load_and_clean("data/cookie_cats.csv")

    os.makedirs(os.path.dirname(output_report_path), exist_ok=True)

    # 1. SRM Check
    n_gate30 = len(df[df["version"] == "gate_30"])
    n_gate40 = len(df[df["version"] == "gate_40"])
    srm_results = check_srm(n_gate30, n_gate40)

    # 2. Retention Tests
    ret1_results = test_retention(df, "retention_1")
    ret7_results = test_retention(df, "retention_7")

    # 3. Engagement Test (Mann-Whitney U)
    eng_results = test_engagement(df)

    # 4. Power & MDE for Day-1 and Day-7 Retention
    power_ret1 = retrospective_power(
        ret1_results["rate_gate30"], ret1_results["rate_gate40"], min(n_gate30, n_gate40)
    )
    power_ret7 = retrospective_power(
        ret7_results["rate_gate30"], ret7_results["rate_gate40"], min(n_gate30, n_gate40)
    )

    all_results = {
        "srm": srm_results,
        "retention_1": ret1_results,
        "retention_7": ret7_results,
        "engagement": eng_results,
        "power_retention_1": power_ret1,
        "power_retention_7": power_ret7,
    }

    # Print summary to console
    print("\n=======================================================")
    print("           STATISTICAL PIPELINE EXECUTION              ")
    print("=======================================================")
    print(f"1. SRM Check: Chi2 = {srm_results['chi2_stat']:.4f}, p = {srm_results['p_value']:.4f} -> {srm_results['verdict']}")
    print(f"2. Day-1 Retention: Gate30 = {ret1_results['rate_gate30']*100:.2f}%, Gate40 = {ret1_results['rate_gate40']*100:.2f}% | Chi2 p = {ret1_results['chi2_p_value']:.4f} (Z p = {ret1_results['z_p_value']:.4f})")
    print(f"3. Day-7 Retention: Gate30 = {ret7_results['rate_gate30']*100:.2f}%, Gate40 = {ret7_results['rate_gate40']*100:.2f}% | Chi2 p = {ret7_results['chi2_p_value']:.4f} (Z p = {ret7_results['z_p_value']:.4f})")
    print(f"4. Engagement (Mann-Whitney U): U = {eng_results['u_stat']:.0f}, p = {eng_results['p_value']:.4f}")
    print(f"5. Day-7 Power: Achieved Power = {power_ret7['achieved_power']:.4f}, MDE (80% power) = {power_ret7['approx_mde_abs_percentage_points']:.2f}% pts")
    print("=======================================================\n")

    return all_results


if __name__ == "__main__":
    run_full_statistical_pipeline()
