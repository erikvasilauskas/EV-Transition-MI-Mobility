"""Automotive supply-chain attribution using the Michigan SAM.

This script reproduces the workflow described by the user: treat the
motor vehicle manufacturing sectors (NAICS 3361-3363 analogues in the
SAM) as the purchasing industries, quantify how much of each commodity
they absorb, and allocate those requirements back to producing
industries via the make table.

When executed, the script writes three CSV files:
- data/intermediate/sam_auto_commodity_shares.csv
- data/intermediate/sam_auto_industry_shares.csv
- data/intermediate/sam_auto_naics_shares.csv

All files land in ``data/intermediate`` by default (the directory will
be created if needed).
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, Mapping

import numpy as np
import pandas as pd

MAKE_TABLE_SHEET = "2017"
SEGMENT_LOOKUP_PATH = Path("data/lookups/segment_assignments.csv")

# Default automotive purchasing industries in the SAM. Update the list or
# supply ``--auto-codes`` if you want a different definition.
DEFAULT_AUTO_CODES: Mapping[int, str] = {
    324: "Automobile and light duty motor vehicle manufacturing",
    325: "Heavy duty truck manufacturing",
    326: "Motor vehicle body manufacturing",
    327: "Truck trailer manufacturing",
    330: "Motor vehicle gasoline engine and engine parts manufacturing",
    331: "Motor vehicle electrical and electronic equipment manufacturing",
    332: "Motor vehicle transmission and power train parts manufacturing",
    333: "Motor vehicle seating and interior trim manufacturing",
    334: "Motor vehicle metal stamping",
    335: "Other motor vehicle parts manufacturing",
    336: "Motor vehicle steering, suspension component (except spring), and brake systems manufacturing",
}


def extract_naics_4(code: str | int | float | None) -> str | None:
    """Return the leading four-digit NAICS fragment when present."""
    if code is None or (isinstance(code, float) and pd.isna(code)):
        return None
    text = str(code).strip()
    if len(text) < 4 or not text[:4].isdigit():
        return None
    return text[:4]


def parse_auto_codes(raw: Iterable[str]) -> set[int]:
    """Parse a sequence of comma-separated code strings into integers."""
    codes: set[int] = set()
    for token in raw:
        pieces = token.split(",")
        for piece in pieces:
            stripped = piece.strip()
            if stripped:
                codes.add(int(stripped))
    return codes


def read_sam(path: Path) -> pd.DataFrame:
    """Load the SAM CSV with numeric Value column."""
    df = pd.read_csv(path, skipinitialspace=True)
    df.columns = df.columns.str.strip()
    df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
    return df.dropna(subset=["Value"]).reset_index(drop=True)


def prepare_numeric_columns(df: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    """Ensure selected columns are numeric Int64, dropping rows with NaNs."""
    for col in columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.dropna(subset=list(columns)).astype({col: "Int64" for col in columns})


def compute_commodity_demand_shares(
    sam: pd.DataFrame, auto_codes: set[int]
) -> pd.DataFrame:
    """Return commodity demand totals and auto demand shares."""
    use = sam[sam["TransferDescription"] == "Commodity Use"].copy()
    use = prepare_numeric_columns(use, ["PayingCode", "ReceivingCode"])

    totals = (
        use.groupby(["ReceivingCode", "ReceivingDescription"], as_index=False)["Value"]
        .sum()
        .rename(columns={"Value": "total_demand"})
    )

    auto_use = use[use["PayingCode"].isin(auto_codes)]
    auto_totals = (
        auto_use.groupby(
            ["ReceivingCode", "ReceivingDescription"], as_index=False
        )["Value"]
        .sum()
        .rename(columns={"Value": "auto_demand"})
    )

    summary = totals.merge(
        auto_totals, on=["ReceivingCode", "ReceivingDescription"], how="left"
    ).fillna({"auto_demand": 0.0})
    summary["auto_share"] = summary["auto_demand"] / summary["total_demand"]
    summary = summary.rename(
        columns={
            "ReceivingCode": "CommodityCode",
            "ReceivingDescription": "CommodityDescription",
        }
    )
    return summary.sort_values("auto_demand", ascending=False).reset_index(drop=True)


def compute_industry_allocation(
    sam: pd.DataFrame, commodity_summary: pd.DataFrame
) -> pd.DataFrame:
    """Allocate automotive commodity demand back to producing industries."""
    make = sam[sam["TransferDescription"] == "Commodity Make"].copy()
    make = prepare_numeric_columns(make, ["PayingCode", "ReceivingCode"])

    make["commodity_output"] = make.groupby("PayingCode")["Value"].transform("sum")
    make["industry_output"] = make.groupby("ReceivingCode")["Value"].transform("sum")
    make["make_share"] = make["Value"] / make["commodity_output"]

    combo = make.merge(
        commodity_summary[
            ["CommodityCode", "auto_demand", "total_demand", "auto_share"]
        ],
        left_on="PayingCode",
        right_on="CommodityCode",
        how="left",
    ).fillna({"auto_demand": 0.0, "total_demand": 0.0, "auto_share": 0.0})

    combo["auto_attributed_output"] = combo["make_share"] * combo["auto_demand"]

    industry_auto = (
        combo.groupby(["ReceivingCode", "ReceivingDescription"], as_index=False)[
            "auto_attributed_output"
        ]
        .sum()
    )

    industry_totals = (
        make.groupby(["ReceivingCode", "ReceivingDescription"], as_index=False)[
            "industry_output"
        ]
        .first()
        .rename(columns={"industry_output": "total_industry_output"})
    )

    result = industry_totals.merge(
        industry_auto,
        on=["ReceivingCode", "ReceivingDescription"],
        how="left",
    ).fillna({"auto_attributed_output": 0.0})

    result["auto_share_of_output"] = (
        result["auto_attributed_output"] / result["total_industry_output"]
    )
    return result.sort_values("auto_attributed_output", ascending=False).reset_index(
        drop=True
    )


def load_bea_industry_crosswalk(make_table_path: Path) -> pd.DataFrame:
    """Load BEA make table metadata and derive NAICS crosswalk."""
    df = pd.read_excel(make_table_path, sheet_name=MAKE_TABLE_SHEET, header=[4, 5])
    meta = df.loc[:, ("Industry / Commodity", slice(None))].rename(
        columns={"Industry / Commodity": "meta"}
    )
    industry_codes = meta[("meta", "Code")]
    industry_desc = meta[("meta", "Industry Description")]

    crosswalk = (
        pd.DataFrame(
            {
                "bea_industry_code": industry_codes,
                "bea_industry_description": industry_desc,
            }
        )
        .dropna(subset=["bea_industry_code", "bea_industry_description"])
        .drop_duplicates(subset=["bea_industry_code"])
    )
    crosswalk["bea_industry_description"] = crosswalk[
        "bea_industry_description"
    ].str.strip()
    crosswalk["naics_code"] = crosswalk["bea_industry_code"].apply(extract_naics_4)
    return crosswalk


def aggregate_to_naics(
    industry_summary: pd.DataFrame,
    crosswalk: pd.DataFrame,
    lookup_path: Path,
) -> pd.DataFrame:
    """Aggregate SAM industry attribution to 4-digit NAICS definitions."""
    merged = industry_summary.merge(
        crosswalk,
        left_on="ReceivingDescription",
        right_on="bea_industry_description",
        how="left",
    )

    unmatched = merged["bea_industry_code"].isna().sum()
    if unmatched:
        print(
            f"Warning: {unmatched} SAM industries did not match BEA descriptions; they will be excluded from NAICS aggregation."
        )

    aggregated = (
        merged.dropna(subset=["naics_code"])
        .groupby("naics_code", as_index=False)[
            ["auto_attributed_output", "total_industry_output"]
        ]
        .sum()
    )
    aggregated["naics_code"] = aggregated["naics_code"].astype(str).str.strip()

    lookup_df = pd.read_csv(lookup_path, dtype={"naics_code": str})
    lookup_df["naics_code"] = lookup_df["naics_code"].str.strip()

    result = lookup_df.merge(aggregated, on="naics_code", how="left")

    for col in ["auto_attributed_output", "total_industry_output"]:
        if col in result.columns:
            result[col] = result[col].fillna(0.0)
        else:
            result[col] = 0.0

    result["auto_share_of_output"] = np.divide(
        result["auto_attributed_output"],
        result["total_industry_output"],
        out=np.zeros(len(result), dtype=float),
        where=result["total_industry_output"] != 0,
    )

    return result.sort_values("auto_attributed_output", ascending=False)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Attribute SAM commodity demand to automotive manufacturing supply chains."
    )
    parser.add_argument(
        "--sam-path",
        type=Path,
        default=Path("data/raw/SAM.csv"),
        help="Path to the SAM CSV export (default: data/raw/SAM.csv).",
    )
    parser.add_argument(
        "--make-table-path",
        type=Path,
        default=Path("data/raw/IOMake_Before_Redefinitions_PRO_Detail.xlsx"),
        help="BEA make table for deriving the NAICS crosswalk (default: data/raw/IOMake_Before_Redefinitions_PRO_Detail.xlsx).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/intermediate"),
        help="Directory for derived CSV outputs (default: data/intermediate).",
    )
    parser.add_argument(
        "--auto-codes",
        nargs="*",
        default=[],
        metavar="CODE",
        help=(
            "Override the automotive purchasing industries with a space- or "
            "comma-separated list of SAM industry codes."
        ),
    )
    args = parser.parse_args()

    if args.auto_codes:
        auto_codes = parse_auto_codes(args.auto_codes)
        unknown = sorted(auto_codes.difference(DEFAULT_AUTO_CODES.keys()))
        if unknown:
            print(
                f"Using {len(auto_codes)} automotive codes (includes unmapped codes: {unknown})"
            )
    else:
        auto_codes = set(DEFAULT_AUTO_CODES.keys())

    sam = read_sam(args.sam_path)
    commodity_summary = compute_commodity_demand_shares(sam, auto_codes)
    industry_summary = compute_industry_allocation(sam, commodity_summary)

    bea_crosswalk = load_bea_industry_crosswalk(args.make_table_path)
    naics_summary = aggregate_to_naics(industry_summary, bea_crosswalk, SEGMENT_LOOKUP_PATH)

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    commodity_path = output_dir / "sam_auto_commodity_shares.csv"
    industry_path = output_dir / "sam_auto_industry_shares.csv"
    naics_path = output_dir / "sam_auto_naics_shares.csv"

    commodity_summary.to_csv(commodity_path, index=False)
    industry_summary.to_csv(industry_path, index=False)
    naics_summary.to_csv(naics_path, index=False)

    top_commodities = commodity_summary.nlargest(10, "auto_demand")[
        ["CommodityDescription", "auto_demand", "auto_share"]
    ]
    top_industries = industry_summary.nlargest(10, "auto_attributed_output")[
        ["ReceivingDescription", "auto_attributed_output", "auto_share_of_output"]
    ]
    top_naics = naics_summary.nlargest(10, "auto_attributed_output")[
        [
            "naics_code",
            "naics_title",
            "auto_attributed_output",
            "auto_share_of_output",
        ]
    ]

    pd.options.display.float_format = "{:,.4f}".format
    print("Top commodities by automotive demand:")
    print(top_commodities.to_string(index=False))
    print("\nTop producing industries attributed to automotive demand:")
    print(top_industries.to_string(index=False))
    print("\nTop NAICS industries attributed to automotive demand:")
    print(top_naics.to_string(index=False))
    print(
        "\nWrote commodity shares to "
        f"{commodity_path}, industry shares to {industry_path}, and NAICS shares to {naics_path}."
    )


if __name__ == "__main__":
    main()
