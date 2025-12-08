"""Trace SAM commodity-use rows that drive automotive shares for 38 NAICS industries.

This script mirrors the v2 attribution logic, but expands the intermediate data
so you can see which IMPLAN Commodity-Use line items contribute to each of the
38 NAICS industries in `data/lookups/segment_assignments.csv`.

Outputs (single Excel workbook):
* `commodity_use_auto_lines` – Commodity Use rows for the automotive buyer set
  with commodity-level auto/total demand and auto_share.
* `naics_make_attribution` – IMPLAN industry → NAICS breakdown of auto-attributed
  output (after weighting by the IMPLAN→NAICS bridge).
* `naics_commodity_use_trace` – Joined view linking the NAICS rows back to the
  underlying Commodity Use line items by commodity, so you can filter by NAICS.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, Set

import numpy as np
import pandas as pd

# Default automotive industries used in the SAM attribution workflow.
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


def parse_codes(values: Iterable[str] | None) -> Set[int]:
    """Parse CLI-provided codes into a set of integers."""
    if not values:
        return set()
    codes: set[int] = set()
    for token in values:
        for piece in str(token).split(","):
            piece = piece.strip()
            if piece:
                codes.add(int(piece))
    return codes


def load_sam(path: Path) -> pd.DataFrame:
    """Load the SAM CSV with consistent numeric types."""
    df = pd.read_csv(path, skipinitialspace=True)
    df.columns = df.columns.str.strip()
    df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
    df["PayingCode"] = pd.to_numeric(df["PayingCode"], errors="coerce").astype("Int64")
    df["ReceivingCode"] = pd.to_numeric(df["ReceivingCode"], errors="coerce").astype("Int64")
    return df.dropna(subset=["Value"])


def load_bridge(path: Path) -> pd.DataFrame:
    """Load and normalize the IMPLAN → NAICS6 bridge weights."""
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


def compute_commodity_shares(
    sam: pd.DataFrame,
    auto_codes: set[int],
) -> pd.DataFrame:
    """Compute auto share for each commodity from Commodity Use."""
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


def build_trace(
    sam_path: Path,
    bridge_path: Path,
    lookup_path: Path,
    output_path: Path,
    auto_codes: set[int],
) -> None:
    """Generate Excel tracing Commodity Use to NAICS industries."""
    sam = load_sam(sam_path)
    bridge = load_bridge(bridge_path)
    lookup = pd.read_csv(lookup_path, dtype={"naics_code": str})
    lookup["naics_code"] = lookup["naics_code"].str.strip()

    commodity_shares = compute_commodity_shares(sam, auto_codes)

    # Commodity Use lines for auto buyers (numerator rows)
    commodity_use = sam[sam["TransferDescription"] == "Commodity Use"].copy()
    auto_use_lines = commodity_use[commodity_use["PayingCode"].isin(auto_codes)].copy()
    auto_use_lines = auto_use_lines.rename(
        columns={
            "PayingCode": "use_paying_code",
            "PayingDescription": "use_paying_description",
            "ReceivingCode": "commodity_code",
            "ReceivingDescription": "commodity_description",
            "Value": "use_value",
        }
    )
    auto_use_lines = auto_use_lines.merge(
        commodity_shares[
            ["commodity_code", "commodity_description", "total_demand", "auto_demand", "auto_share"]
        ],
        on=["commodity_code", "commodity_description"],
        how="left",
    )

    # Make table with auto attribution
    make = sam[sam["TransferDescription"] == "Commodity Make"].copy()
    auto_share_map = commodity_shares.set_index("commodity_code")["auto_share"]
    make["auto_share"] = make["PayingCode"].map(auto_share_map).fillna(0.0)
    make["auto_component"] = make["Value"] * make["auto_share"]
    make = make.rename(
        columns={
            "PayingCode": "commodity_code",
            "PayingDescription": "commodity_description",
            "ReceivingCode": "implan_code",
            "ReceivingDescription": "implan_description",
            "Value": "make_value",
        }
    )

    # Bridge to NAICS and filter to the 38 NAICS (naics_code is NAICS4)
    make_bridge = make.merge(
        bridge[["implan_code", "naics6", "naics6_title", "weight"]],
        on="implan_code",
        how="left",
    )
    make_bridge["weight"] = make_bridge["weight"].fillna(0.0)
    make_bridge["naics6"] = make_bridge["naics6"].fillna("")
    make_bridge["naics4"] = make_bridge["naics6"].str.slice(0, 4)
    make_bridge["weighted_auto_component"] = make_bridge["auto_component"] * make_bridge["weight"]

    lookup_filtered = lookup.rename(columns={"naics_code": "naics4"})
    make_lookup = make_bridge.merge(
        lookup_filtered, on="naics4", how="inner"
    )  # inner keeps only the 38 industries

    # Link NAICS rows back to the Commodity Use lines for the same commodity.
    trace = make_lookup.merge(
        auto_use_lines[
            [
                "commodity_code",
                "commodity_description",
                "use_paying_code",
                "use_paying_description",
                "use_value",
                "auto_share",
                "total_demand",
                "auto_demand",
            ]
        ],
        on=["commodity_code", "commodity_description", "auto_share"],
        how="left",
    )
    # Drop rows with zero auto attribution to keep the trace focused.
    trace = trace[trace["auto_component"] > 0].copy()

    # Summaries: NAICS-level auto attribution (post-weighting).
    naics_summary = (
        make_lookup.groupby(
            ["naics4", "naics_title", "segment_id", "segment_name", "stage"], as_index=False
        )["weighted_auto_component"]
        .sum()
        .rename(columns={"weighted_auto_component": "auto_attributed_output"})
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        auto_use_lines.to_excel(writer, sheet_name="commodity_use_auto_lines", index=False)
        make_lookup.to_excel(writer, sheet_name="naics_make_attribution", index=False)
        trace.to_excel(writer, sheet_name="naics_commodity_use_trace", index=False)
        naics_summary.to_excel(writer, sheet_name="naics_summary", index=False)

    print(
        f"Wrote trace workbook with {len(trace):,} traced rows and "
        f"{len(auto_use_lines):,} auto Commodity Use rows to {output_path}"
    )


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Trace IMPLAN Commodity Use rows that drive auto shares for the 38 NAICS industries."
    )
    parser.add_argument(
        "--sam-path",
        type=Path,
        default=repo_root / "data" / "raw" / "SAM.csv",
        help="Path to SAM CSV (default: data/raw/SAM.csv)",
    )
    parser.add_argument(
        "--bridge-path",
        type=Path,
        default=repo_root / "data" / "raw" / "Bridge_2022NaicsToImplan528_AllDescriptions.xlsx",
        help="IMPLAN→NAICS6 bridge (default: data/raw/Bridge_2022NaicsToImplan528_AllDescriptions.xlsx)",
    )
    parser.add_argument(
        "--lookup-path",
        type=Path,
        default=repo_root / "data" / "lookups" / "segment_assignments.csv",
        help="38-industry lookup (default: data/lookups/segment_assignments.csv)",
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        default=repo_root / "data" / "interim" / "sam_naics_commodity_use_trace.xlsx",
        help="Excel destination (default: data/interim/sam_naics_commodity_use_trace.xlsx)",
    )
    parser.add_argument(
        "--auto-codes",
        nargs="*",
        help="Override default automotive buying industries (space- or comma-separated).",
    )

    args = parser.parse_args()
    codes = parse_codes(args.auto_codes) or DEFAULT_AUTO_CODES
    build_trace(
        sam_path=args.sam_path,
        bridge_path=args.bridge_path,
        lookup_path=args.lookup_path,
        output_path=args.output_path,
        auto_codes=codes,
    )


if __name__ == "__main__":
    main()
