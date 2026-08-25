"""SQL Layer module using in-memory DuckDB for Cookie Cats A/B Testing.

This module registers the cleaned dataset into an in-memory DuckDB instance,
runs analytical SQL queries (group counts, retention rates, engagement metrics),
and exports clean CSV artifacts for downstream Power BI dashboard integration.
"""

import os
import sys
from typing import Tuple
import duckdb
import pandas as pd

# Support both direct script execution and package imports
try:
    from src.data_prep import load_and_clean
except ModuleNotFoundError:
    from data_prep import load_and_clean


def run_sql_layer(
    df: pd.DataFrame = None,
    output_dir: str = "outputs"
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Execute SQL aggregation queries using DuckDB and export artifacts.

    Parameters
    ----------
    df : pd.DataFrame, optional
        The cleaned DataFrame. If None, load_and_clean() will be invoked.
    output_dir : str, optional
        Directory path where Power BI CSV imports will be saved.

    Returns
    -------
    Tuple[pd.DataFrame, pd.DataFrame]
        Tuple of (df_group_sizes, df_group_summary).
    """
    if df is None:
        df = load_and_clean("data/cookie_cats.csv")

    os.makedirs(output_dir, exist_ok=True)

    # Initialize in-memory DuckDB connection
    con = duckdb.connect(database=":memory:")

    # Register the cleaned pandas DataFrame as a SQL table
    con.register("cookie_cats", df)

    # ---------------------------------------------------------
    # Query 1: Group sizes check
    # ---------------------------------------------------------
    query_group_sizes = """
    -- Query 1: Calculate total user count per experimental variant
    SELECT 
        version,
        COUNT(*) AS n_users
    FROM cookie_cats
    GROUP BY version
    ORDER BY version ASC;
    """
    df_group_sizes = con.execute(query_group_sizes).df()
    print("\n--- [DuckDB SQL Query 1: Group Sizes] ---")
    print(df_group_sizes)

    # ---------------------------------------------------------
    # Query 2: Group summary aggregation
    # Computes sample sizes, Day-1/Day-7 retention rates, 
    # mean game rounds, and median game rounds.
    # ---------------------------------------------------------
    query_group_summary = """
    -- Query 2: Comprehensive A/B variant performance summary
    SELECT 
        version,
        COUNT(*) AS n_users,
        ROUND(AVG(CASE WHEN retention_1 THEN 1.0 ELSE 0.0 END), 4) AS retention_1_rate,
        ROUND(AVG(CASE WHEN retention_7 THEN 1.0 ELSE 0.0 END), 4) AS retention_7_rate,
        ROUND(AVG(sum_gamerounds), 2) AS avg_rounds_played,
        ROUND(MEDIAN(sum_gamerounds), 2) AS median_rounds_played
    FROM cookie_cats
    GROUP BY version
    ORDER BY version ASC;
    """
    df_group_summary = con.execute(query_group_summary).df()
    print("\n--- [DuckDB SQL Query 2: Group Summary] ---")
    print(df_group_summary)

    # ---------------------------------------------------------
    # Export Power BI Deliverables
    # ---------------------------------------------------------
    summary_path = os.path.join(output_dir, "summary_by_group.csv")
    cleaned_path = os.path.join(output_dir, "cleaned_data.csv")

    df_group_summary.to_csv(summary_path, index=False)
    df.to_csv(cleaned_path, index=False)

    print(f"\n[SQL LAYER] Exported summary table to: {summary_path}")
    print(f"[SQL LAYER] Exported cleaned dataset to: {cleaned_path}")

    return df_group_sizes, df_group_summary


if __name__ == "__main__":
    run_sql_layer()
