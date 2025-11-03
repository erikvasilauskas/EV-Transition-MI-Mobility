"""Flexible SAM automotive supply-chain attribution with CLI parameters.

This script mirrors the logic in ``build_sam_auto_shares_v2.py`` but adds
command-line options so we can generate outputs for multiple SAM inputs
(e.g., Michigan vs. US) without overwriting the defaults.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, Tuple

import numpy as np
import pandas as pd

# Default automotive purchasing industries in the SAM. Update or override via --auto-codes.
DEFAULT_AUTO_CODES = {
    324,
    325,
    326,
    327,
    330,
    331,
    332,
    333,
    334,
    335,
    336,
}


def parse_auto_codes(values: Iterable[str]) -> set[int]:
    """Convert command-line auto code tokens into integers."""
    codes: set[int] = set()
    for token in values:
        for piece in str(token).split(","):
            piece = piece.strip()
            if piece:
                codes.add(int(piece))
    return codes


def load_sam(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, skipinitialspace=True)
    df.columns = df.columns.str.strip()
    df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
    df["PayingCode"] = pd.to_numeric(df["PayingCode"], errors="coerce").astype("Int64")
    df["ReceivingCode"] = pd.to_numeric(df["ReceivingCode"], errors="coerce").astype("Int64")
    return df.dropna(subset=["Value"])


def compute_commodity_auto_shares(sam: pd.DataFrame, auto_codes: set[int]) -> pd.DataFrame:
    use = sam[sam["TransferDescription"] == "Commodity Use"].copy()
    totals = (
        use.groupby(["ReceivingCode", "ReceivingDescription"], as_index=False)["Value"]
        .sum()
        .rename(columns={"Value": "total_demand"})
    )

    auto_use = use[use["PayingCode"].isin(auto_codes)]
    auto_totals = (
        auto_use.groupby(["ReceivingCode", "ReceivingDescription"], as_index=False)["Value"]
        .sum()
        .rename(columns={"Value": "auto_demand"})
    )

    merged = totals.merge(
        auto_totals, on=["ReceivingCode", "ReceivingDescription"], how="left"
    ).fillna({"auto_demand": 0.0})
    merged["auto_share"] = np.divide(
        merged["auto_demand"],
        merged["total_demand"],
        out=np.zeros(len(merged), dtype=float),
        where=merged["total_demand"] != 0,
    )
    return merged.rename(
        columns={
            "ReceivingCode": "commodity_code",
            "ReceivingDescription": "commodity_description",
        }
    )


def compute_industry_shares_from_industry_use(sam: pd.DataFrame, auto_codes: set[int]) -> pd.DataFrame:
    use = sam[sam["TransferDescription"] == "Industry Use"].copy()
    foreign_mask = use["PayingDescription"].str.contains("Foreign Trade", case=False, na=False)
    use = use[~foreign_mask].copy()
    totals = (
        use.groupby(["PayingCode", "PayingDescription"], as_index=False)["Value"]
        .sum()
        .rename(columns={"Value": "total_industry_output"})
    )
    auto_use = use[use["ReceivingCode"].isin(auto_codes)]
    auto_totals = (
        auto_use.groupby(["PayingCode", "PayingDescription"], as_index=False)["Value"]
        .sum()
        .rename(columns={"Value": "auto_attributed_output"})
    )
    merged = totals.merge(
        auto_totals, on=["PayingCode", "PayingDescription"], how="left"
    ).fillna({"auto_attributed_output": 0.0})
    merged = merged.rename(
        columns={
            "PayingCode": "ReceivingCode",
            "PayingDescription": "ReceivingDescription",
        }
    )
    merged["auto_share_of_output"] = np.divide(
        merged["auto_attributed_output"],
        merged["total_industry_output"],
        out=np.zeros(len(merged), dtype=float),
        where=merged["total_industry_output"] != 0,
    )
    return merged


def load_bridge(path: Path) -> pd.DataFrame:
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
    df["weight"] = pd.to_numeric(df["weight"], errors="coerce").fillna(0.0)

    def _normalize(group: pd.Series) -> pd.Series:
        total = group.sum()
        if total == 0 or pd.isna(total):
            if len(group) == 0:
                return group
            return pd.Series(np.repeat(1.0 / len(group), len(group)), index=group.index)
        return group / total

    df["weight"] = df.groupby("implan_code")["weight"].transform(_normalize)
    return df


def aggregate_sam_industry_shares(
    sam: pd.DataFrame,
    commodity_shares: pd.DataFrame,
) -> pd.DataFrame:
    make = sam[sam["TransferDescription"] == "Commodity Make"].copy()
    make = make.merge(
        commodity_shares[["commodity_code", "auto_share"]],
        left_on="PayingCode",
        right_on="commodity_code",
        how="left",
    ).fillna({"auto_share": 0.0})

    make["auto_component"] = make["Value"] * make["auto_share"]

    industry_totals = (
        make.groupby(["ReceivingCode", "ReceivingDescription"], as_index=False)["Value"]
        .sum()
        .rename(columns={"Value": "total_industry_output"})
    )
    industry_auto = (
        make.groupby(["ReceivingCode", "ReceivingDescription"], as_index=False)["auto_component"]
        .sum()
        .rename(columns={"auto_component": "auto_attributed_output"})
    )

    result = industry_totals.merge(
        industry_auto, on=["ReceivingCode", "ReceivingDescription"], how="left"
    )
    result["auto_attributed_output"] = result["auto_attributed_output"].fillna(0.0)
    result["auto_share_of_output"] = np.divide(
        result["auto_attributed_output"],
        result["total_industry_output"],
        out=np.zeros(len(result), dtype=float),
        where=result["total_industry_output"] != 0,
    )
    return result


def distribute_to_naics_levels(
    industry_df: pd.DataFrame,
    bridge_df: pd.DataFrame,
    agg_df: pd.DataFrame,
    lookup_df: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    merge_df = industry_df.merge(
        bridge_df[["implan_code", "naics6", "naics6_title", "weight"]],
        left_on="ReceivingCode",
        right_on="implan_code",
        how="left",
    )

    merge_df["weight"] = merge_df["weight"].fillna(0.0)
    merge_df["weighted_auto_output"] = merge_df["auto_attributed_output"] * merge_df["weight"]
    merge_df["weighted_total_output"] = merge_df["total_industry_output"] * merge_df["weight"]

    naics6 = (
        merge_df.groupby(["naics6", "naics6_title"], as_index=False)[[
            "weighted_auto_output",
            "weighted_total_output",
        ]]
        .sum()
    )
    naics6["auto_share_of_output"] = np.divide(
        naics6["weighted_auto_output"],
        naics6["weighted_total_output"],
        out=np.zeros(len(naics6), dtype=float),
        where=naics6["weighted_total_output"] != 0,
    )

    merge_df["naics4"] = merge_df["naics6"].str.slice(0, 4)
    naics4 = (
        merge_df.groupby("naics4", as_index=False)[[
            "weighted_auto_output",
            "weighted_total_output",
        ]]
        .sum()
    )
    naics4["auto_share_of_output"] = np.divide(
        naics4["weighted_auto_output"],
        naics4["weighted_total_output"],
        out=np.zeros(len(naics4), dtype=float),
        where=naics4["weighted_total_output"] != 0,
    )

    lookup = lookup_df.copy()
    lookup["naics_code"] = lookup["naics_code"].astype(str).str.strip()
    lookup["naics4"] = lookup["naics_code"].str.slice(0, 4)

    lookup_results = lookup.merge(
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
    lookup_results["auto_attributed_output"] = lookup_results["auto_attributed_output"].fillna(0.0)
    lookup_results["total_industry_output"] = lookup_results["total_industry_output"].fillna(0.0)
    lookup_results["auto_share_of_output"] = np.divide(
        lookup_results["auto_attributed_output"],
        lookup_results["total_industry_output"],
        out=np.zeros(len(lookup_results), dtype=float),
        where=lookup_results["total_industry_output"] != 0,
    )

    agg_merge = industry_df.merge(
        agg_df,
        left_on="ReceivingCode",
        right_on="implan_code",
        how="left",
    )
    agg_grouped = (
        agg_merge.dropna(subset=["naics_agg_code"])
        .groupby(["naics_agg_code", "naics_agg_title"], as_index=False)[
            ["auto_attributed_output", "total_industry_output"]
        ]
        .sum()
    )
    agg_grouped["auto_share_of_output"] = np.divide(
        agg_grouped["auto_attributed_output"],
        agg_grouped["total_industry_output"],
        out=np.zeros(len(agg_grouped), dtype=float),
        where=agg_grouped["total_industry_output"] != 0,
    )

    return naics6, naics4, lookup_results, agg_grouped


def load_aggregated_naics(path: Path) -> pd.DataFrame:
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compute SAM-based auto attribution shares.")
    parser.add_argument("--sam-path", type=Path, default=None, help="SAM CSV path (default: data/raw/SAM.csv)")
    parser.add_argument(
        "--bridge-path",
        type=Path,
        default=None,
        help="Bridge_2022NaicsToImplan528_AllDescriptions.xlsx path.",
    )
    parser.add_argument(
        "--agg-path",
        type=Path,
        default=None,
        help="Implan528toAggregated2022Naics.xlsx path.",
    )
    parser.add_argument(
        "--lookup-path",
        type=Path,
        default=None,
        help="Segment lookup CSV (default: data/lookups/segment_assignments.csv).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory (default: data/intermediate/sam_naics_shares_v2).",
    )
    parser.add_argument(
        "--auto-codes",
        nargs="*",
        default=[],
        metavar="CODE",
        help="Override automotive purchasing industries with SAM codes (space/comma separated).",
    )
    parser.add_argument(
        "--label",
        type=str,
        default="",
        help="Optional suffix for output filenames (e.g., 'us' -> *_us.csv).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]

    sam_path = args.sam_path if args.sam_path else repo_root / "data" / "raw" / "SAM.csv"
    bridge_path = args.bridge_path if args.bridge_path else repo_root / "data" / "raw" / "Bridge_2022NaicsToImplan528_AllDescriptions.xlsx"
    agg_path = args.agg_path if args.agg_path else repo_root / "data" / "raw" / "Implan528toAggregated2022Naics.xlsx"
    lookup_path = args.lookup_path if args.lookup_path else repo_root / "data" / "lookups" / "segment_assignments.csv"
    output_dir = args.output_dir if args.output_dir else repo_root / "data" / "intermediate" / "sam_naics_shares_v2"
    output_dir.mkdir(parents=True, exist_ok=True)

    auto_codes = parse_auto_codes(args.auto_codes) if args.auto_codes else set(DEFAULT_AUTO_CODES)

    sam = load_sam(sam_path)
    descriptions = set(sam["TransferDescription"].unique())
    bridge = load_bridge(bridge_path)
    agg_mapping = load_aggregated_naics(agg_path)
    lookup_df = pd.read_csv(lookup_path, dtype={"naics_code": str})

    if {"Commodity Use", "Commodity Make"}.issubset(descriptions):
        commodity_shares = compute_commodity_auto_shares(sam, auto_codes)
        industry_shares = aggregate_sam_industry_shares(sam, commodity_shares)
    elif "Industry Use" in descriptions:
        commodity_shares = None
        industry_shares = compute_industry_shares_from_industry_use(sam, auto_codes)
    else:
        raise ValueError("SAM must contain Commodity Use/Make or Industry Use flows for attribution.")
    naics6, naics4, lookup_results, agg_grouped = distribute_to_naics_levels(
        industry_shares,
        bridge,
        agg_mapping,
        lookup_df,
    )

    label_suffix = f"_{args.label.strip()}" if args.label else ""

    if commodity_shares is not None:
        commodity_out = output_dir / f"sam_auto_commodity_shares{label_suffix}.csv"
        commodity_shares.to_csv(commodity_out, index=False)

    industry_out = output_dir / f"sam_auto_implan_shares{label_suffix}.csv"
    naics6_out = output_dir / f"sam_auto_naics6_shares{label_suffix}.csv"
    naics4_out = output_dir / f"sam_auto_naics4_mobility38{label_suffix}.csv"
    agg_out = output_dir / f"sam_auto_naics_aggregated_shares{label_suffix}.csv"

    industry_shares.to_csv(industry_out, index=False)
    naics6.to_csv(naics6_out, index=False)
    lookup_results.to_csv(naics4_out, index=False)
    agg_grouped.to_csv(agg_out, index=False)

    print(f"Wrote SAM industry shares: {industry_out}")
    print(f"Wrote NAICS6 shares: {naics6_out}")
    print(f"Wrote NAICS4 mobility shares: {naics4_out}")
    print(f"Wrote aggregated NAICS shares: {agg_out}")


if __name__ == "__main__":
    main()
