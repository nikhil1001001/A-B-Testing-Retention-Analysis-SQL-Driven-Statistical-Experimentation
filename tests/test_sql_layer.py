"""Unit tests for src/sql_layer.py."""

import os
import shutil
import tempfile
import pandas as pd
import pytest
from src.sql_layer import run_sql_layer


def test_sql_layer_aggregations():
    """Verify DuckDB SQL aggregation computes accurate group summaries on known data."""
    test_df = pd.DataFrame({
        "userid": [1, 2, 3, 4],
        "version": ["gate_30", "gate_30", "gate_40", "gate_40"],
        "sum_gamerounds": [10, 20, 30, 50],
        "retention_1": [True, False, True, True],
        "retention_7": [True, False, False, False],
    })

    temp_dir = tempfile.mkdtemp()
    try:
        df_sizes, df_summary = run_sql_layer(df=test_df, output_dir=temp_dir)

        # Check group sizes
        assert len(df_sizes) == 2
        assert df_sizes[df_sizes["version"] == "gate_30"]["n_users"].iloc[0] == 2
        assert df_sizes[df_sizes["version"] == "gate_40"]["n_users"].iloc[0] == 2

        # Check summary aggregations
        g30_sum = df_summary[df_summary["version"] == "gate_30"].iloc[0]
        g40_sum = df_summary[df_summary["version"] == "gate_40"].iloc[0]

        assert g30_sum["retention_1_rate"] == 0.50
        assert g30_sum["retention_7_rate"] == 0.50
        assert g30_sum["avg_rounds_played"] == 15.0
        assert g30_sum["median_rounds_played"] == 15.0

        assert g40_sum["retention_1_rate"] == 1.00
        assert g40_sum["retention_7_rate"] == 0.00
        assert g40_sum["avg_rounds_played"] == 40.0
        assert g40_sum["median_rounds_played"] == 40.0

        # Check exported files
        assert os.path.exists(os.path.join(temp_dir, "summary_by_group.csv"))
        assert os.path.exists(os.path.join(temp_dir, "cleaned_data.csv"))
    finally:
        shutil.rmtree(temp_dir)
