"""Bootstrap resampling module for Cookie Cats A/B Testing.

This module computes empirical percentile bootstrap confidence intervals
for differences in retention rates between gate_30 and gate_40 without
relying on asymptotic normality assumptions.
"""

import os
import sys
from typing import Dict, Any, Tuple
import numpy as np
import pandas as pd

# Support both direct script execution and package imports
try:
    from src.data_prep import load_and_clean
except ModuleNotFoundError:
    from data_prep import load_and_clean


def bootstrap_diff(
    group_a: np.ndarray,
    group_b: np.ndarray,
    n_boot: int = 10000,
    ci: float = 0.95,
    seed: int = 42
) -> Dict[str, Any]:
    """Calculate the bootstrap distribution of the difference in means (proportions).

    Optimized for high-throughput resampling using binomial sampling equivalence
    for binary data and chunked index sampling for general arrays.

    Parameters
    ----------
    group_a : np.ndarray
        Array of binary or continuous outcomes for Group A (e.g. gate_30).
    group_b : np.ndarray
        Array of binary or continuous outcomes for Group B (e.g. gate_40).
    n_boot : int, default 10000
        Number of bootstrap resamples.
    ci : float, default 0.95
        Confidence level for the empirical percentile interval.
    seed : int, default 42
        Random seed for reproducibility.

    Returns
    -------
    Dict[str, Any]
        Dictionary containing mean difference, empirical percentile CI,
        standard error, and probability that Group A > Group B.
    """
    rng = np.random.default_rng(seed)
    n_a = len(group_a)
    n_b = len(group_b)

    observed_mean_a = float(np.mean(group_a))
    observed_mean_b = float(np.mean(group_b))
    observed_diff = observed_mean_b - observed_mean_a

    is_binary_a = np.array_equal(group_a, group_a.astype(bool))
    is_binary_b = np.array_equal(group_b, group_b.astype(bool))

    if is_binary_a and is_binary_b:
        # Exact non-parametric bootstrap equivalence for Bernoulli outcomes
        # Drawing N samples with replacement from N Bernoulli trials with proportion p
        # is mathematically identical to drawing from Binomial(N, p) / N.
        boot_means_a = rng.binomial(n=n_a, p=observed_mean_a, size=n_boot) / n_a
        boot_means_b = rng.binomial(n=n_b, p=observed_mean_b, size=n_boot) / n_b
    else:
        # Chunked vectorized resampling for arbitrary continuous distributions
        chunk_size = 1000
        boot_means_a_list = []
        boot_means_b_list = []
        
        for _ in range(0, n_boot, chunk_size):
            cur_n = min(chunk_size, n_boot - len(boot_means_a_list))
            idx_a = rng.integers(0, n_a, size=(cur_n, n_a))
            idx_b = rng.integers(0, n_b, size=(cur_n, n_b))
            boot_means_a_list.extend(np.mean(group_a[idx_a], axis=1))
            boot_means_b_list.extend(np.mean(group_b[idx_b], axis=1))
            
        boot_means_a = np.array(boot_means_a_list)
        boot_means_b = np.array(boot_means_b_list)

    # Treatment - Control difference (gate_40 - gate_30)
    boot_diffs = boot_means_b - boot_means_a

    # Percentile confidence interval
    alpha = 1.0 - ci
    lower_pct = (alpha / 2.0) * 100
    upper_pct = (1.0 - alpha / 2.0) * 100

    ci_lower = float(np.percentile(boot_diffs, lower_pct))
    ci_upper = float(np.percentile(boot_diffs, upper_pct))
    boot_mean_diff = float(np.mean(boot_diffs))
    boot_se = float(np.std(boot_diffs, ddof=1))

    # Empirical probability that Control is superior to Treatment: P(gate_30 > gate_40)
    prob_a_greater_b = float(np.mean(boot_diffs < 0))

    return {
        "n_boot": n_boot,
        "ci_level": ci,
        "observed_diff": observed_diff,
        "bootstrap_mean_diff": boot_mean_diff,
        "bootstrap_se": boot_se,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "prob_gate30_greater_gate40": prob_a_greater_b,
        "bootstrap_differences": boot_diffs,
    }


def run_bootstrap_analysis(
    df: pd.DataFrame = None,
    n_boot: int = 10000
) -> Dict[str, Any]:
    """Execute bootstrap analysis for both Day-1 and Day-7 retention metrics.

    Parameters
    ----------
    df : pd.DataFrame, optional
        Cleaned Cookie Cats DataFrame.
    n_boot : int, default 10000
        Number of resamples.

    Returns
    -------
    Dict[str, Any]
        Dictionary with bootstrap results for retention_1 and retention_7.
    """
    if df is None:
        df = load_and_clean("data/cookie_cats.csv")

    gate30_ret1 = df[df["version"] == "gate_30"]["retention_1"].astype(int).values
    gate40_ret1 = df[df["version"] == "gate_40"]["retention_1"].astype(int).values

    gate30_ret7 = df[df["version"] == "gate_30"]["retention_7"].astype(int).values
    gate40_ret7 = df[df["version"] == "gate_40"]["retention_7"].astype(int).values

    print(f"\n[BOOTSTRAP] Running {n_boot:,} bootstrap iterations for Day-1 & Day-7 Retention...")
    res_ret1 = bootstrap_diff(gate30_ret1, gate40_ret1, n_boot=n_boot)
    res_ret7 = bootstrap_diff(gate30_ret7, gate40_ret7, n_boot=n_boot)

    print("\n--- [Bootstrap Results: Day-1 Retention Difference (gate_40 - gate_30)] ---")
    print(f"Mean Difference: {res_ret1['bootstrap_mean_diff']*100:.4f}% pts")
    print(f"95% Percentile CI: [{res_ret1['ci_lower']*100:.4f}%, {res_ret1['ci_upper']*100:.4f}%]")
    print(f"P(gate_30 > gate_40): {res_ret1['prob_gate30_greater_gate40']*100:.2f}%")

    print("\n--- [Bootstrap Results: Day-7 Retention Difference (gate_40 - gate_30)] ---")
    print(f"Mean Difference: {res_ret7['bootstrap_mean_diff']*100:.4f}% pts")
    print(f"95% Percentile CI: [{res_ret7['ci_lower']*100:.4f}%, {res_ret7['ci_upper']*100:.4f}%]")
    print(f"P(gate_30 > gate_40): {res_ret7['prob_gate30_greater_gate40']*100:.2f}%")

    return {"retention_1": res_ret1, "retention_7": res_ret7}


if __name__ == "__main__":
    run_bootstrap_analysis()
