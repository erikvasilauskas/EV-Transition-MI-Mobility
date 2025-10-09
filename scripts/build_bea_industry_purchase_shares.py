#!/usr/bin/env python3
"""
Transform commodity-based BEA purchase shares into industry-based shares using the
2017 Make table.

Inputs
------
- data/interim/bea_domestic_use_target_naics.csv
    Commodity-level usage data with Moody-adjusted intermediate inputs.
- data/raw/IOMake_Before_Redefinitions_PRO_Detail.xlsx (sheet='2017')
    Make table used to distribute commodity supply across producing industries.
- data/lookups/segment_assignments.csv
    Metadata for the 38 target NAICS industries.

Outputs
-------
- data/interim/bea_domestic_use_industry_purchases.csv
    Industry-level allocations of motor vehicle purchases with share metrics.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd


MAKE_TOTAL_ROW = "T007"


def load_detail_data(path: Path) -> pd.DataFrame:
    """Load commodity detail data and enforce numeric types."""
    df = pd.read_csv(path, dtype={"Code": str, "NAICS": str})
    numeric_cols = ["3361MV", "T001_Intermediate Inputs", "Total Commodity Output"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    return df


def load_make_table(path: Path, sheet: str = "2017") -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Load the BEA Make table and return a matrix of industry by commodity values."""
    df = pd.read_excel(path, sheet_name=sheet, header=[4, 5])
    df = df.rename(columns={"Industry / Commodity": "meta"})

    industry_codes = df[("meta", "Code")]
    industry_desc = df[("meta", "Industry Description")]
    df.index = industry_codes

    commodity_cols = [
        col
        for col in df.columns
        if col[0] != "meta" and not pd.isna(col[1])
    ]
    commodity_codes = [str(col[1]) for col in commodity_cols]

    value_matrix = df[commodity_cols].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    value_matrix.columns = commodity_codes

    # Drop rows without valid industry codes or representing overall totals.
    value_matrix = value_matrix.loc[~value_matrix.index.isna()]
    value_matrix = value_matrix.drop(index=[MAKE_TOTAL_ROW], errors="ignore")

    industry_metadata = (
        pd.DataFrame({"industry_code": industry_codes, "industry_description": industry_desc})
        .dropna(subset=["industry_code"])
        .drop_duplicates(subset=["industry_code"])
        .set_index("industry_code")
    )

    return value_matrix, industry_metadata


def compute_make_shares(make_matrix: pd.DataFrame) -> pd.DataFrame:
    """Convert the make matrix to commodity production shares by industry."""
    col_sums = make_matrix.sum(axis=0)
    valid_cols = col_sums[col_sums > 0].index
    filtered = make_matrix.loc[:, valid_cols]

    shares = filtered.div(col_sums[valid_cols], axis=1)
    shares = shares.stack(future_stack=True).reset_index()
    shares.columns = ["industry_code", "commodity_code", "industry_make_share"]

    return shares


def extract_naics_4(code: str) -> str | None:
    """Extract the leading four-digit NAICS code when available."""
    if not isinstance(code, str):
        code = str(code)

    match = re.match(r"(\d{4})", code)
    return match.group(1) if match else None


def allocate_to_industries(
    detail_df: pd.DataFrame,
    make_shares: pd.DataFrame,
) -> pd.DataFrame:
    """Allocate commodity purchases and totals to producing industries."""
    merged = detail_df.merge(
        make_shares,
        left_on="Code",
        right_on="commodity_code",
        how="inner",
    )

    merged["mv_purchase_alloc"] = merged["3361MV"] * merged["industry_make_share"]
    merged["intermediate_alloc"] = (
        merged["T001_Intermediate Inputs"] * merged["industry_make_share"]
    )
    merged["total_output_alloc"] = (
        merged["Total Commodity Output"] * merged["industry_make_share"]
    )

    grouped = (
        merged.groupby("industry_code", as_index=False)[
            ["mv_purchase_alloc", "intermediate_alloc", "total_output_alloc"]
        ]
        .sum()
    )

    grouped["naics_code"] = grouped["industry_code"].apply(extract_naics_4)
    grouped = grouped.dropna(subset=["naics_code"])

    return grouped


def aggregate_to_target_naics(
    industry_allocations: pd.DataFrame,
    metadata: pd.DataFrame,
) -> pd.DataFrame:
    """Aggregate industry allocations to the 4-digit target NAICS list and add metadata."""
    aggregated = (
        industry_allocations.groupby("naics_code", as_index=False)[
            ["mv_purchase_alloc", "intermediate_alloc", "total_output_alloc"]
        ]
        .sum()
    )

    result = aggregated.merge(metadata, on="naics_code", how="inner")

    result["share_of_intermediate_inputs_industry"] = np.divide(
        result["mv_purchase_alloc"],
        result["intermediate_alloc"],
        out=np.full(result.shape[0], np.nan, dtype=float),
        where=result["intermediate_alloc"] != 0,
    )
    result["share_of_industry_output_to_motor_vehicles"] = np.divide(
        result["mv_purchase_alloc"],
        result["total_output_alloc"],
        out=np.full(result.shape[0], np.nan, dtype=float),
        where=result["total_output_alloc"] != 0,
    )

    return result


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]

    detail_path = repo_root / "data" / "interim" / "bea_domestic_use_target_naics.csv"
    make_path = repo_root / "data" / "raw" / "IOMake_Before_Redefinitions_PRO_Detail.xlsx"
    lookup_path = repo_root / "data" / "lookups" / "segment_assignments.csv"
    output_path = repo_root / "data" / "interim" / "bea_domestic_use_industry_purchases.csv"

    detail_df = load_detail_data(detail_path)
    make_matrix, industry_metadata = load_make_table(make_path)
    make_shares = compute_make_shares(make_matrix)
    industry_allocations = allocate_to_industries(detail_df, make_shares)

    lookup_df = pd.read_csv(lookup_path, dtype={"naics_code": str})
    lookup_df["naics_code"] = lookup_df["naics_code"].str.strip()

    result = aggregate_to_target_naics(industry_allocations, lookup_df)
    result = result.sort_values("naics_code")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False)


if __name__ == "__main__":
    main()
