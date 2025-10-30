"""Derive SAM automotive shares mapped to NAICS codes using IMPLAN crosswalks.

This script augments the earlier BEA-based approach by leaning on the
IMPLAN 528-sector to NAICS concordances that now live in
``data/raw``. It produces three artifacts:

* Aggregated NAICS shares using ``Implan528toAggregated2022Naics.xlsx``.
* Six-digit NAICS allocations using ``Bridge_2022NaicsToImplan528_AllDescriptions.xlsx``.
* Four-digit mobility supply-chain shares (38 industries) derived from
  the six-digit allocations and the existing segment lookup.

All outputs are written under ``data/intermediate/sam_naics_shares``.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from pathlib import Path


def load_sam_industry_shares(path: Path) -> pd.DataFrame:
    """Read SAM industry-level automotive shares."""
    df = pd.read_csv(path)
    df["ReceivingCode"] = pd.to_numeric(df["ReceivingCode"], errors="coerce").astype("Int64")
    return df


def load_implan_to_naics_agg(path: Path) -> pd.DataFrame:
    """Load the IMPLAN-to-aggregated NAICS mapping."""
    df = pd.read_excel(path)
    df = df.rename(
        columns={
            "Implan528Index": "implan_code",
            "Implan528Description": "implan_description",
            "2022NaicsCode": "naics_agg_code",
            "NaicsTitle": "naics_agg_title",
        }
    )
    df = df.dropna(subset=["implan_code", "naics_agg_code"])
    df["implan_code"] = pd.to_numeric(df["implan_code"], errors="coerce").astype("Int64")
    df["naics_agg_code"] = df["naics_agg_code"].astype(str).str.strip()
    df["naics_agg_title"] = df["naics_agg_title"].astype(str).str.strip()
    return df[["implan_code", "naics_agg_code", "naics_agg_title"]]


def normalize_weights(series: pd.Series) -> pd.Series:
    """Ensure weights sum to one within each IMPLAN sector."""
    total = series.sum()
    if pd.isna(total) or total == 0:
        if len(series) == 0:
            return series
        return pd.Series([1.0 / len(series)] * len(series), index=series.index)
    return series / total


def load_bridge_to_naics6(path: Path) -> pd.DataFrame:
    """Load the detailed IMPLAN-to-NAICS6 mapping with CEW ratios."""
    df = pd.read_excel(path)
    df = df.rename(
        columns={
            "Implan528Index": "implan_code",
            "Implan528Description": "implan_description",
            "2022NaicsCode": "naics6",
            "2022NaicsTitle": "naics6_title",
            "CewEmpRatio": "weight",
        }
    )
    df = df.dropna(subset=["implan_code", "naics6"])
    df["implan_code"] = pd.to_numeric(df["implan_code"], errors="coerce").astype("Int64")
    df["naics6"] = df["naics6"].astype(str).str.zfill(6)
    df["naics6_title"] = df["naics6_title"].astype(str).str.strip()
    df["weight"] = pd.to_numeric(df["weight"], errors="coerce")
    df["weight"] = df["weight"].fillna(0.0)
    df["weight"] = df.groupby("implan_code")["weight"].transform(normalize_weights)
    return df[["implan_code", "naics6", "naics6_title", "weight"]]


def compute_naics_shares_from_bridge(
    sam_df: pd.DataFrame,
    bridge_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Allocate SAM industry totals to NAICS6 and derive NAICS4 aggregates."""
    merged = sam_df.merge(
        bridge_df,
        left_on="ReceivingCode",
        right_on="implan_code",
        how="inner",
    )

    merged["weighted_auto_output"] = merged["auto_attributed_output"] * merged["weight"]
    merged["weighted_total_output"] = merged["total_industry_output"] * merged["weight"]

    naics6 = (
        merged.groupby(["naics6", "naics6_title"], as_index=False)[
            ["weighted_auto_output", "weighted_total_output"]
        ]
        .sum()
    )
    naics6["auto_share_of_output"] = np.divide(
        naics6["weighted_auto_output"],
        naics6["weighted_total_output"],
        out=np.zeros(len(naics6), dtype=float),
        where=naics6["weighted_total_output"] != 0,
    )

    merged["naics4"] = merged["naics6"].str[:4]
    naics4 = (
        merged.groupby("naics4", as_index=False)[
            ["weighted_auto_output", "weighted_total_output"]
        ]
        .sum()
    )
    naics4["auto_share_of_output"] = np.divide(
        naics4["weighted_auto_output"],
        naics4["weighted_total_output"],
        out=np.zeros(len(naics4), dtype=float),
        where=naics4["weighted_total_output"] != 0,
    )

    return naics6, naics4


def compute_naics_shares_from_agg(
    sam_df: pd.DataFrame,
    agg_df: pd.DataFrame,
) -> pd.DataFrame:
    """Aggregate SAM industry totals using the coarse NAICS mapping."""
    merged = sam_df.merge(
        agg_df,
        left_on="ReceivingCode",
        right_on="implan_code",
        how="left",
    )
    unmatched = merged["naics_agg_code"].isna().sum()
    if unmatched:
        print(f"Warning: {unmatched} SAM industries lacked an aggregated NAICS mapping.")

    grouped = (
        merged.dropna(subset=["naics_agg_code"])
        .groupby(["naics_agg_code", "naics_agg_title"], as_index=False)[
            ["auto_attributed_output", "total_industry_output"]
        ]
        .sum()
    )
    grouped["auto_share_of_output"] = np.divide(
        grouped["auto_attributed_output"],
        grouped["total_industry_output"],
        out=np.zeros(len(grouped), dtype=float),
        where=grouped["total_industry_output"] != 0,
    )
    return grouped


def align_with_lookup(
    naics4: pd.DataFrame,
    lookup_path: Path,
) -> pd.DataFrame:
    """Map NAICS4 totals onto the 38-industry segment lookup."""
    lookup = pd.read_csv(lookup_path, dtype={"naics_code": str})
    lookup["naics_code"] = lookup["naics_code"].str.strip()

    aligned = lookup.merge(
        naics4.rename(
            columns={
                "naics4": "naics_code",
                "weighted_auto_output": "auto_attributed_output",
                "weighted_total_output": "total_industry_output",
            }
        ),
        on="naics_code",
        how="left",
    )

    for col in ["auto_attributed_output", "total_industry_output"]:
        aligned[col] = aligned[col].fillna(0.0)

    aligned["auto_share_of_output"] = np.divide(
        aligned["auto_attributed_output"],
        aligned["total_industry_output"],
        out=np.zeros(len(aligned), dtype=float),
        where=aligned["total_industry_output"] != 0,
    )

    return aligned


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sam_path = repo_root / "data" / "intermediate" / "sam_auto_industry_shares.csv"
    agg_path = repo_root / "data" / "raw" / "Implan528toAggregated2022Naics.xlsx"
    bridge_path = repo_root / "data" / "raw" / "Bridge_2022NaicsToImplan528_AllDescriptions.xlsx"
    lookup_path = repo_root / "data" / "lookups" / "segment_assignments.csv"
    output_dir = repo_root / "data" / "intermediate" / "sam_naics_shares"
    output_dir.mkdir(parents=True, exist_ok=True)

    sam_df = load_sam_industry_shares(sam_path)
    agg_df = load_implan_to_naics_agg(agg_path)
    bridge_df = load_bridge_to_naics6(bridge_path)

    agg_shares = compute_naics_shares_from_agg(sam_df, agg_df)
    naics6, naics4 = compute_naics_shares_from_bridge(sam_df, bridge_df)
    mobility38 = align_with_lookup(naics4, lookup_path)

    agg_file = output_dir / "sam_auto_naics_aggregated_shares.csv"
    naics6_file = output_dir / "sam_auto_naics6_shares.csv"
    naics4_file = output_dir / "sam_auto_naics4_mobility38.csv"

    agg_shares.to_csv(agg_file, index=False)
    naics6.to_csv(naics6_file, index=False)
    mobility38.to_csv(naics4_file, index=False)

    print("Wrote aggregated NAICS shares:", agg_file)
    print("Wrote six-digit NAICS shares:", naics6_file)
    print("Wrote mobility 38 NAICS shares:", naics4_file)

    if not mobility38["auto_share_of_output"].any():
        print(
            "Warning: mobility 38 output contains zero attributed output across the board. "
            "Double-check the crosswalk coverage."
        )


if __name__ == "__main__":
    main()
