"""Compile automotive attribution shares from multiple sources into a single table.

Inputs
------
- data/intermediate/sam_naics_shares_v2/sam_auto_naics4_mobility38.csv
    SAM-derived auto shares with segment metadata.
- data/raw/auto_attribution_core_auto_lightcast.csv
- data/raw/auto_attribution_bea.csv
- data/interim/bea_share_three_way_summary_with_table.csv
- data/raw/bea_detailed_io_prorates.csv
- data/raw/MRIO Industry Shares - Tyler.csv

Output
------
- data/intermediate/auto_share_comparison.csv
    Includes original SAM columns plus aligned share estimates from each source.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def _percent_to_float(series: pd.Series) -> pd.Series:
    """Convert percent strings (e.g., '12.3%') to float proportions."""
    return (
        series.astype(str)
        .str.replace("%", "", regex=False)
        .str.replace(",", "", regex=False)
        .replace({"nan": np.nan, "": np.nan})
        .astype(float)
        .div(100.0)
    )


def load_sam_base(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"naics_code": str})
    df["naics_code"] = df["naics_code"].str.strip()
    df = df.rename(columns={"auto_share_of_output": "sam_auto_share"})
    return df


def load_lightcast(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"naics4": str})
    df["naics4"] = df["naics4"].str.strip()
    return df.rename(columns={"share_to_set": "lightcast_share"})[
        ["naics4", "lightcast_share"]
    ]


def load_legacy_bea(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"NAICS": str})
    df["NAICS"] = df["NAICS"].str.strip()
    return df.rename(columns={"bea_share_to_set": "legacy_bea_share"})[
        ["NAICS", "legacy_bea_share"]
    ]


def load_bea_three_way(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"NAICS": str})
    df["NAICS"] = df["NAICS"].str.strip()
    df["bea_summary_total_output_share"] = _percent_to_float(
        df["Legacy BEA Share of Total Industry Output (Summary Table)"]
    )
    df["bea_detail_intermediate_share"] = _percent_to_float(
        df["BEA Industry Share of Intermediate Inputs (Detailed Table 2017)"]
    )
    df["bea_detail_total_output_share"] = _percent_to_float(
        df["BEA Industry Share of Total Industry Output (Detailed Table 2017)"]
    )
    return df[
        [
            "NAICS",
            "bea_summary_total_output_share",
            "bea_detail_intermediate_share",
            "bea_detail_total_output_share",
        ]
    ]


def load_mrio(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"NAICS": str})
    df["NAICS"] = df["NAICS"].str.strip()
    df["mrio_indirect_share"] = _percent_to_float(df["MRIO_Indirect Share"])
    df["mrio_total_share"] = _percent_to_float(df["MRIO_Total Share"])
    return df[["NAICS", "mrio_indirect_share", "mrio_total_share"]]


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sam_path = repo_root / "data" / "intermediate" / "sam_naics_shares_v2" / "sam_auto_naics4_mobility38.csv"
    lightcast_path = repo_root / "data" / "raw" / "auto_attribution_core_auto_lightcast.csv"
    legacy_bea_path = repo_root / "data" / "raw" / "auto_attribution_bea.csv"
    bea_three_way_path = repo_root / "data" / "interim" / "bea_share_three_way_summary_with_table.csv"
    mrio_path = repo_root / "data" / "raw" / "MRIO Industry Shares - Tyler.csv"
    output_path = repo_root / "data" / "intermediate" / "auto_share_comparison.csv"

    sam_df = load_sam_base(sam_path)
    lightcast_df = load_lightcast(lightcast_path)
    legacy_bea_df = load_legacy_bea(legacy_bea_path)
    bea_three_df = load_bea_three_way(bea_three_way_path)
    mrio_df = load_mrio(mrio_path)

    comparison = sam_df.merge(
        lightcast_df, left_on="naics_code", right_on="naics4", how="left"
    ).drop(columns=["naics4"], errors="ignore")

    comparison = comparison.merge(
        legacy_bea_df, left_on="naics_code", right_on="NAICS", how="left"
    ).drop(columns=["NAICS"], errors="ignore")

    comparison = comparison.merge(
        bea_three_df, left_on="naics_code", right_on="NAICS", how="left", suffixes=("", "_bea3")
    ).drop(columns=["NAICS"], errors="ignore")

    comparison = comparison.merge(
        mrio_df, left_on="naics_code", right_on="NAICS", how="left", suffixes=("", "_mrio")
    ).drop(columns=["NAICS"], errors="ignore")

    # Reorder columns: metadata first, then SAM share, then other shares.
    meta_cols = [
        "naics_code",
        "naics_title",
        "segment_id",
        "segment_name",
        "stage",
        "employment_qcew_2024",
        "mi_employment_pct_change_2024_2030",
        "mi_wage_pct_change_2024_2030",
        "mi_gdp_pct_change_2024_2030",
        "auto_attributed_output",
        "total_industry_output",
        "sam_auto_share",
    ]
    share_cols = [
        "lightcast_share",
        "legacy_bea_share",
        "bea_summary_total_output_share",
        "bea_detail_intermediate_share",
        "bea_detail_total_output_share",
        "mrio_indirect_share",
        "mrio_total_share",
    ]

    # Ensure all requested columns exist (fill missing).
    for col in share_cols:
        if col not in comparison.columns:
            comparison[col] = np.nan

    comparison = comparison[meta_cols + share_cols]
    comparison.to_csv(output_path, index=False)
    print(f"Wrote comparative shares to {output_path}")


if __name__ == "__main__":
    main()
