"""Peeking simulation module for Cookie Cats A/B Testing.

This module simulates sequential hypothesis testing as sample size accumulates
over time (using userid order as an explicitly labeled proxy for player arrival order).
It demonstrates the statistical risk of 'peeking' (continuous monitoring without
alpha-spending corrections) and visualizes the running p-value trajectory.
"""

import os
import sys
from typing import Dict, Any, List
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from statsmodels.stats.proportion import proportions_ztest

# Support both direct script execution and package imports
try:
    from src.data_prep import load_and_clean
except ModuleNotFoundError:
    from data_prep import load_and_clean


def simulate_peeking(
    df: pd.DataFrame = None,
    metric: str = "retention_7",
    step_size: int = 1500,
    min_samples: int = 3000,
    output_plot_path: str = "outputs/peeking_simulation.png",
    seed: int = 42
) -> Dict[str, Any]:
    """Simulate sequential testing as sample size accumulates sequentially.

    NOTE: The Cookie Cats dataset does not contain explicit event timestamps.
    Therefore, this simulation uses the sequential order of `userid` as an explicitly
    labeled proxy for user arrival order over the course of the experiment.

    Parameters
    ----------
    df : pd.DataFrame, optional
        Cleaned Cookie Cats DataFrame.
    metric : str, default 'retention_7'
        Metric to track ('retention_1' or 'retention_7').
    step_size : int, default 1500
        Number of additional users between each simulated statistical 'peek'.
    min_samples : int, default 3000
        Minimum initial sample size before evaluating the first p-value.
    output_plot_path : str, default 'outputs/peeking_simulation.png'
        Filepath to save the resulting simulation visualization.
    seed : int, default 42
        Random seed.

    Returns
    -------
    Dict[str, Any]
        Dictionary with sample size steps, running p-values, running differences,
        and peeking diagnostics.
    """
    if df is None:
        df = load_and_clean("data/cookie_cats.csv")

    os.makedirs(os.path.dirname(output_plot_path), exist_ok=True)

    # Sort by userid as a documented proxy for player arrival order
    df_sorted = df.sort_values(by="userid").reset_index(drop=True)
    total_n = len(df_sorted)

    sample_sizes: List[int] = []
    p_values: List[float] = []
    diffs_pct: List[float] = []
    gate30_rates: List[float] = []
    gate40_rates: List[float] = []

    for n in range(min_samples, total_n + 1, step_size):
        sub_df = df_sorted.iloc[:n]
        
        g30 = sub_df[sub_df["version"] == "gate_30"]
        g40 = sub_df[sub_df["version"] == "gate_40"]

        n_g30 = len(g30)
        n_g40 = len(g40)

        # Skip if one of the groups has too few observations
        if n_g30 < 50 or n_g40 < 50:
            continue

        ret_g30 = int(g30[metric].sum())
        ret_g40 = int(g40[metric].sum())

        p_g30 = ret_g30 / n_g30
        p_g40 = ret_g40 / n_g40

        counts = np.array([ret_g30, ret_g40])
        nobs = np.array([n_g30, n_g40])

        _, p_val = proportions_ztest(count=counts, nobs=nobs, alternative="two-sided")

        sample_sizes.append(n)
        p_values.append(float(p_val))
        diffs_pct.append(float((p_g40 - p_g30) * 100))
        gate30_rates.append(p_g30)
        gate40_rates.append(p_g40)

    # If the exact total_n was not reached in the loop, add final point
    if sample_sizes[-1] != total_n:
        g30 = df_sorted[df_sorted["version"] == "gate_30"]
        g40 = df_sorted[df_sorted["version"] == "gate_40"]
        counts = np.array([int(g30[metric].sum()), int(g40[metric].sum())])
        nobs = np.array([len(g30), len(g40)])
        _, p_val = proportions_ztest(count=counts, nobs=nobs, alternative="two-sided")
        sample_sizes.append(total_n)
        p_values.append(float(p_val))
        diffs_pct.append(float((np.mean(g40[metric]) - np.mean(g30[metric])) * 100))

    p_values_arr = np.array(p_values)
    times_crossed_05 = int(np.sum(p_values_arr < 0.05))
    times_tested = len(p_values)

    # ---------------------------------------------------------
    # Visualization: Peeking Simulation Plot
    # ---------------------------------------------------------
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 8), sharex=True)

    # Top panel: P-value vs Cumulative N
    ax1.plot(sample_sizes, p_values, color="#1f77b4", lw=2, label="Running P-Value (Two-Sided Z-test)")
    ax1.axhline(0.05, color="#d62728", linestyle="--", lw=1.5, label="Standard Significance Threshold (α = 0.05)")
    ax1.axhline(0.01, color="#ff7f0e", linestyle=":", lw=1.5, label="Strict Significance Threshold (α = 0.01)")
    ax1.fill_between(sample_sizes, 0, 0.05, color="#d62728", alpha=0.08, label="Significant Region (p < 0.05)")
    ax1.set_ylabel("P-Value", fontsize=11, fontweight="bold")
    ax1.set_title(
        f"Sequential Peeking Simulation: Running P-Value vs Cumulative Sample Size ({metric.replace('_', ' ').title()})\n"
        "[Note: User ID sequence utilized as an explicit proxy for arrival order]",
        fontsize=12,
        fontweight="bold"
    )
    ax1.set_ylim(-0.02, 1.02)
    ax1.legend(loc="upper right", frameon=True)
    ax1.grid(True, linestyle="--", alpha=0.6)

    # Bottom panel: Running Percentage Point Difference
    ax2.plot(sample_sizes, diffs_pct, color="#2ca02c", lw=2, label="Observed Lift: Gate 40 - Gate 30 (% pts)")
    ax2.axhline(0.0, color="gray", linestyle="-", lw=1)
    ax2.set_xlabel("Cumulative Sample Size (N Users)", fontsize=11, fontweight="bold")
    ax2.set_ylabel("Retention Difference (% pts)", fontsize=11, fontweight="bold")
    ax2.set_title(f"Running Absolute Difference in {metric.replace('_', ' ').title()} (% pts)", fontsize=11)
    ax2.legend(loc="lower right", frameon=True)
    ax2.grid(True, linestyle="--", alpha=0.6)

    plt.tight_layout()
    fig.savefig(output_plot_path, dpi=150)
    plt.close(fig)

    print(f"\n[PEEKING SIMULATION] Evaluated {times_tested} sequential peeking checkpoints.")
    print(f"[PEEKING SIMULATION] P-value dropped below alpha = 0.05 in {times_crossed_05} of {times_tested} checks.")
    print(f"[PEEKING SIMULATION] Plot saved to: {output_plot_path}")

    return {
        "metric": metric,
        "total_checks": times_tested,
        "times_below_05": times_crossed_05,
        "final_p_value": p_values[-1],
        "final_diff_pct": diffs_pct[-1],
        "plot_path": output_plot_path,
    }


if __name__ == "__main__":
    simulate_peeking()
