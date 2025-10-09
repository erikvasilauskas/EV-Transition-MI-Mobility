#!/usr/bin/env python3
"""
Generate BEA domestic use extracts for target NAICS industries.

Outputs
-------
data/interim/bea_domestic_use_target_naics.csv
    Row-level subset of BEA domestic use data restricted to target NAICS codes.

data/interim/bea_domestic_use_target_naics_summary.csv
    NAICS-level aggregation with segment metadata and share calculations.

data/interim/bea_domestic_use_target_naics_match_status.csv
    Lookup NAICS list with an indicator showing whether BEA data matched.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

import numpy as np
import pandas as pd


def load_bea_data(path: Path) -> pd.DataFrame:
    """Read the BEA domestic use Excel file with string NAICS codes."""
    return pd.read_excel(
        path,
        dtype={"NAICS": str, "Code": str},
        engine="openpyxl",
    )


def load_lookup(path: Path) -> pd.DataFrame:
    """Load the NAICS lookup with descriptive metadata."""
    df = pd.read_csv(path, dtype={"naics_code": str})
    df["naics_code"] = df["naics_code"].str.strip()
    return df


def ensure_naics_format(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """Standardize NAICS values to four-character strings."""
    df[column] = (
        df[column]
        .astype(str)
        .str.replace(r"\.0$", "", regex=True)
        .str.strip()
        .str.zfill(4)
    )
    return df


def select_numeric_columns(df: pd.DataFrame) -> List[str]:
    """Identify numeric columns to aggregate."""
    return df.select_dtypes(include=["number"]).columns.tolist()


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]

    bea_path = repo_root / "data" / "raw" / "bea_domestic_use_of_commodities_detail.xlsx"
    lookup_path = repo_root / "data" / "lookups" / "segment_assignments.csv"
    output_dir = repo_root / "data" / "interim"
    output_dir.mkdir(parents=True, exist_ok=True)

    intermediate_path = output_dir / "bea_domestic_use_target_naics.csv"
    summary_path = output_dir / "bea_domestic_use_target_naics_summary.csv"
    match_status_path = output_dir / "bea_domestic_use_target_naics_match_status.csv"

    bea_df = load_bea_data(bea_path)
    bea_df = ensure_naics_format(bea_df, "NAICS")

    lookup_df = load_lookup(lookup_path)
    lookup_df = ensure_naics_format(lookup_df, "naics_code")

    target_naics = set(lookup_df["naics_code"].unique())
    filtered_df = bea_df[bea_df["NAICS"].isin(target_naics)].copy()
    filtered_df.sort_values(["NAICS", "Code"], inplace=True)

    filtered_df.to_csv(intermediate_path, index=False)

    numeric_cols = select_numeric_columns(filtered_df)
    grouped = filtered_df.groupby("NAICS", as_index=False)[numeric_cols].sum()

    metadata_cols = [
        "naics_code",
        "naics_title",
        "segment_id",
        "segment_name",
        "stage",
    ]
    metadata = lookup_df[metadata_cols].drop_duplicates("naics_code")

    summary = grouped.merge(
        metadata,
        left_on="NAICS",
        right_on="naics_code",
        how="left",
    )
    summary.drop(columns=["naics_code"], inplace=True)

    numerator_intermediate = "3361MV"
    denominator_intermediate = "T001_Intermediate Inputs"

    numerator_total_output = "3361MC" if "3361MC" in summary.columns else "3361MV"
    denominator_total_output = "Total Commodity Output"

    for column in [numerator_intermediate, denominator_intermediate, denominator_total_output]:
        if column not in summary.columns:
            raise KeyError(f"Required column '{column}' not found in aggregated data.")

    summary["share_of_intermediate_inputs"] = np.divide(
        summary[numerator_intermediate],
        summary[denominator_intermediate],
        out=np.full(summary.shape[0], np.nan, dtype=float),
        where=summary[denominator_intermediate] != 0,
    )
    summary["share_of_total_commodity_output"] = np.divide(
        summary[numerator_total_output],
        summary[denominator_total_output],
        out=np.full(summary.shape[0], np.nan, dtype=float),
        where=summary[denominator_total_output] != 0,
    )

    summary.sort_values("NAICS", inplace=True)
    summary.to_csv(summary_path, index=False)

    match_status = metadata.rename(columns={"naics_code": "NAICS"}).copy()
    match_status["matched_to_bea"] = match_status["NAICS"].isin(filtered_df["NAICS"])
    match_status.sort_values("NAICS", inplace=True)
    match_status.to_csv(match_status_path, index=False)


if __name__ == "__main__":
    main()
