"""Data preparation and cleaning module for Cookie Cats A/B Testing analysis.

This module handles loading raw data, validating schema integrity,
identifying extreme outliers in game rounds played, and returning
a clean DataFrame ready for downstream SQL aggregation and statistical testing.
"""

from typing import Tuple
import pandas as pd
import numpy as np


def load_and_clean(filepath: str = "data/cookie_cats.csv") -> pd.DataFrame:
    """Load the Cookie Cats dataset, inspect for extreme outliers, and clean it.

    Parameters
    ----------
    filepath : str
        Path to the raw CSV data file.

    Returns
    -------
    pd.DataFrame
        Cleaned DataFrame with the extreme outlier excluded and validated dtypes.
    """
    df = pd.read_csv(filepath)
    initial_row_count = len(df)

    # Validate basic schema
    expected_cols = {"userid", "version", "sum_gamerounds", "retention_1", "retention_7"}
    if not expected_cols.issubset(set(df.columns)):
        raise ValueError(
            f"Dataset missing expected columns. Expected {expected_cols}, got {set(df.columns)}"
        )

    # Sort descending by sum_gamerounds to inspect the upper tail
    df_sorted = df.sort_values(by="sum_gamerounds", ascending=False)
    top_5 = df_sorted.head(5)[["userid", "version", "sum_gamerounds"]]

    top_row = top_5.iloc[0]
    second_row = top_5.iloc[1]

    # Verify if top value is genuinely disconnected from the rest
    # (e.g., top value is > 10x the second highest value)
    is_disconnected = top_row["sum_gamerounds"] > (second_row["sum_gamerounds"] * 5)

    if is_disconnected:
        outlier_userid = int(top_row["userid"])
        outlier_rounds = int(top_row["sum_gamerounds"])
        second_rounds = int(second_row["sum_gamerounds"])

        print(
            f"[DATA CLEANING] Identified disconnected extreme outlier:\n"
            f"  - UserID: {outlier_userid}\n"
            f"  - Gamerounds: {outlier_rounds:,} (Next highest player had {second_rounds:,} rounds)\n"
            f"  - Action: Dropping UserID {outlier_userid} to prevent distortion of engagement statistics."
        )

        # Drop the single disconnected outlier
        cleaned_df = df[df["userid"] != outlier_userid].copy()
    else:
        cleaned_df = df.copy()

    # Verify no null values exist
    null_counts = cleaned_df.isnull().sum().to_dict()
    if any(count > 0 for count in null_counts.values()):
        print(f"[DATA CLEANING WARNING] Missing values detected: {null_counts}")
        cleaned_df = cleaned_df.dropna()

    # Standardize data types
    cleaned_df["userid"] = cleaned_df["userid"].astype(int)
    cleaned_df["version"] = cleaned_df["version"].astype(str)
    cleaned_df["sum_gamerounds"] = cleaned_df["sum_gamerounds"].astype(int)
    cleaned_df["retention_1"] = cleaned_df["retention_1"].astype(bool)
    cleaned_df["retention_7"] = cleaned_df["retention_7"].astype(bool)

    print(
        f"[DATA CLEANING] Initial rows: {initial_row_count:,} | "
        f"Cleaned rows: {len(cleaned_df):,} | "
        f"Dropped: {initial_row_count - len(cleaned_df)} row(s)"
    )

    return cleaned_df


if __name__ == "__main__":
    df_clean = load_and_clean("data/cookie_cats.csv")
    print("\nCleaned Data Summary:")
    print(df_clean.info())
    print("\nGroup Counts:")
    print(df_clean["version"].value_counts())
