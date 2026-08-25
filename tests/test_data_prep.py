"""Unit tests for src/data_prep.py."""

import os
import tempfile
import pandas as pd
import pytest
from src.data_prep import load_and_clean


def test_load_and_clean_real_dataset():
    """Verify that loading the real dataset drops exactly 1 outlier and returns 90,188 rows."""
    if os.path.exists("data/cookie_cats.csv"):
        df = load_and_clean("data/cookie_cats.csv")
        assert len(df) == 90188
        assert 6390605 not in df["userid"].values
        assert set(df["version"].unique()) == {"gate_30", "gate_40"}
        assert df["retention_1"].dtype == bool
        assert df["retention_7"].dtype == bool


def test_load_and_clean_synthetic_outlier():
    """Verify that an extreme disconnected outlier is identified and dropped."""
    synthetic_data = pd.DataFrame({
        "userid": [1, 2, 3, 4, 5, 999],
        "version": ["gate_30", "gate_30", "gate_40", "gate_40", "gate_30", "gate_30"],
        "sum_gamerounds": [10, 20, 15, 25, 30, 50000],
        "retention_1": [True, False, True, False, True, False],
        "retention_7": [False, False, True, False, True, False],
    })

    with tempfile.NamedTemporaryFile(suffix=".csv", mode="w+", delete=False) as tmp:
        synthetic_data.to_csv(tmp.name, index=False)
        tmp_path = tmp.name

    try:
        cleaned = load_and_clean(tmp_path)
        assert len(cleaned) == 5
        assert 999 not in cleaned["userid"].values
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_load_and_clean_missing_columns():
    """Verify ValueError is raised if required columns are missing."""
    invalid_data = pd.DataFrame({"userid": [1, 2], "version": ["gate_30", "gate_40"]})
    with tempfile.NamedTemporaryFile(suffix=".csv", mode="w+", delete=False) as tmp:
        invalid_data.to_csv(tmp.name, index=False)
        tmp_path = tmp.name

    try:
        with pytest.raises(ValueError, match="Dataset missing expected columns"):
            load_and_clean(tmp_path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
