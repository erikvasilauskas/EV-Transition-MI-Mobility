#!/usr/bin/env python3
"""
Compile three approaches to BEA attribution shares:
1. Legacy summary-table shares.
2. Commodity-based detailed shares.
3. Industry-based shares derived via the Make table.

Output is sorted according to the segment ordering in the lookup table.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict

import pandas as pd


def load_lookup(path: Path) -> pd.DataFrame:
    """Load segment lookup and establish the desired sort order."""
    lookup = pd.read_csv(path, dtype={"naics_code": str})
    lookup["naics_code"] = lookup["naics_code"].str.strip().str.zfill(4)
    lookup["segment_sort_order"] = range(len(lookup))
    return lookup


def load_comparison(path: Path) -> pd.DataFrame:
    """Read the legacy vs commodity comparison file and rename share columns."""
    comparison = pd.read_csv(path, dtype={"naics_code": str})
    comparison["naics_code"] = comparison["naics_code"].str.strip().str.zfill(4)

    rename_map: Dict[str, str] = {
        "share_of_intermediate_inputs": "commodity_share_of_intermediate_inputs",
        "share_of_total_commodity_output": "commodity_share_of_total_output",
    }
    comparison.rename(columns=rename_map, inplace=True)

    numeric_cols = [
        "legacy_bea_share_to_set",
        "commodity_share_of_intermediate_inputs",
        "commodity_share_of_total_output",
    ]
    for col in numeric_cols:
        if col in comparison.columns:
            comparison[col] = pd.to_numeric(comparison[col], errors="coerce")

    return comparison[
        [
            "naics_code",
            "legacy_stage",
            "legacy_sector",
            "legacy_naics_title",
            "legacy_bea_share_to_set",
            "commodity_share_of_intermediate_inputs",
            "commodity_share_of_total_output",
            "merge_status",
        ]
    ]


def load_industry_shares(path: Path) -> pd.DataFrame:
    """Read industry-allocated shares and rename columns for clarity."""
    industry = pd.read_csv(path, dtype={"naics_code": str})
    industry["naics_code"] = industry["naics_code"].str.strip().str.zfill(4)

    rename_map = {
        "share_of_intermediate_inputs_industry": "industry_share_of_intermediate_inputs",
        "share_of_industry_output_to_motor_vehicles": "industry_share_of_total_output",
    }
    industry.rename(columns=rename_map, inplace=True)

    numeric_cols = [
        "mv_purchase_alloc",
        "intermediate_alloc",
        "total_output_alloc",
        "industry_share_of_intermediate_inputs",
        "industry_share_of_total_output",
    ]
    for col in numeric_cols:
        if col in industry.columns:
            industry[col] = pd.to_numeric(industry[col], errors="coerce")

    return industry[
        [
            "naics_code",
            "mv_purchase_alloc",
            "intermediate_alloc",
            "total_output_alloc",
            "industry_share_of_intermediate_inputs",
            "industry_share_of_total_output",
        ]
    ]


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]

    lookup_path = repo_root / "data" / "lookups" / "segment_assignments.csv"
    comparison_path = repo_root / "data" / "interim" / "bea_auto_attribution_comparison.csv"
    industry_path = repo_root / "data" / "interim" / "bea_domestic_use_industry_purchases.csv"
    output_path = repo_root / "data" / "interim" / "bea_share_three_way_summary.csv"

    lookup = load_lookup(lookup_path)
    comparison = load_comparison(comparison_path)
    industry = load_industry_shares(industry_path)

    base_columns = [
        "segment_sort_order",
        "naics_code",
        "naics_title",
        "segment_id",
        "segment_name",
        "stage",
    ]
    base = lookup[base_columns]

    merged = base.merge(comparison, on="naics_code", how="left")
    merged = merged.merge(industry, on="naics_code", how="left")

    merged.sort_values("segment_sort_order", inplace=True)
    merged.drop(columns=["segment_sort_order"], inplace=True)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(output_path, index=False)


if __name__ == "__main__":
    main()

