"""Unit tests for src/bootstrap.py."""

import numpy as np
import pytest
from src.bootstrap import bootstrap_diff


def test_bootstrap_diff_known_delta():
    """Verify bootstrap confidence interval contains the true population difference."""
    rng = np.random.default_rng(42)
    # Group A: p = 0.20, Group B: p = 0.25 (Difference = +0.05)
    group_a = rng.binomial(n=1, p=0.20, size=5000)
    group_b = rng.binomial(n=1, p=0.25, size=5000)

    res = bootstrap_diff(group_a, group_b, n_boot=2000, ci=0.95, seed=42)

    assert res["n_boot"] == 2000
    assert res["ci_lower"] < 0.05 < res["ci_upper"]
    assert res["prob_gate30_greater_gate40"] < 0.05  # Group B is clearly higher


def test_bootstrap_diff_null_case():
    """Verify bootstrap CI spans zero when groups are drawn from identical distributions."""
    rng = np.random.default_rng(123)
    group_a = rng.binomial(n=1, p=0.40, size=3000)
    group_b = rng.binomial(n=1, p=0.40, size=3000)

    res = bootstrap_diff(group_a, group_b, n_boot=2000, ci=0.95, seed=123)

    assert res["ci_lower"] < 0.0 < res["ci_upper"]
    assert 0.30 < res["prob_gate30_greater_gate40"] < 0.70
