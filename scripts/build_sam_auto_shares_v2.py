"""Single-pass SAM automotive supply-chain attribution (upstream & downstream).

This script reads the SAM CSV and IMPLAN-to-NAICS bridges, then produces
automotive attribution metrics for:

* IMPLAN/SAM industries
* NAICS 6-digit codes
* NAICS 4-digit mobility segments (38 industries)
* Aggregated NAICS codes from the coarse IMPLAN concordance

It supersedes earlier two-step workflows by handling the entire process
from raw SAM to final outputs. Results are written under
``data/intermediate/sam_naics_shares_v2``.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


AUTO_INDUSTRY_CODES = {
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


def load_sam(path: Path) -> pd.DataFrame:
    """Load the SAM CSV and ensure consistent numeric fields."""
    df = pd.read_csv(path, skipinitialspace=True)
    df.columns = df.columns.str.strip()
    df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
    df["PayingCode"] = pd.to_numeric(df["PayingCode"], errors="coerce").astype("Int64")
    df["ReceivingCode"] = pd.to_numeric(df["ReceivingCode"], errors="coerce").astype("Int64")
    return df.dropna(subset=["Value"])


def compute_commodity_auto_shares(sam: pd.DataFrame) -> pd.DataFrame:
    """Return the share of each commodity's demand coming from auto industries."""
    use = sam[sam["TransferDescription"] == "Commodity Use"].copy()
    totals = (
        use.groupby(["ReceivingCode", "ReceivingDescription"], as_index=False)["Value"]
        .sum()
        .rename(columns={"Value": "total_demand"})
    )

    auto_use = use[use["PayingCode"].isin(AUTO_INDUSTRY_CODES)]
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


def load_bridge(path: Path) -> pd.DataFrame:
    """Load the 2022 NAICS to IMPLAN mapping with CEW employment ratios."""
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

    # Normalize weights within each IMPLAN sector; if zero, assign equal shares.
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
    """Compute automotive attribution for all SAM industries."""
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
        make.groupby(["ReceivingCode", "ReceivingDescription"], as_index=False)[
            "auto_component"
        ]
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
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Allocate SAM industry results to NAICS6, NAICS4, aggregated NAICS, and lookup 38."""
    # Merge with detailed bridge (NAICS6)
    merged = industry_df.merge(
        bridge_df[["implan_code", "naics6", "naics6_title", "weight"]],
        left_on="ReceivingCode",
        right_on="implan_code",
        how="left",
    )
    merged["weight"] = merged["weight"].fillna(0.0)
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

    # NAICS4 roll-up
    merged["naics4"] = merged["naics6"].str.slice(0, 4)
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

    # Align with 38-industry lookup
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

    # Aggregated NAICS (coarse)
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
    """Load the coarse IMPLAN-to-aggregated NAICS mapping."""
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


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sam_path = repo_root / "data" / "raw" / "SAM.csv"
    bridge_path = repo_root / "data" / "raw" / "Bridge_2022NaicsToImplan528_AllDescriptions.xlsx"
    agg_path = repo_root / "data" / "raw" / "Implan528toAggregated2022Naics.xlsx"
    lookup_path = repo_root / "data" / "lookups" / "segment_assignments.csv"
    output_dir = repo_root / "data" / "intermediate" / "sam_naics_shares_v2"
    output_dir.mkdir(parents=True, exist_ok=True)

    sam = load_sam(sam_path)
    commodity_shares = compute_commodity_auto_shares(sam)
    bridge = load_bridge(bridge_path)
    agg_mapping = load_aggregated_naics(agg_path)
    lookup_df = pd.read_csv(lookup_path, dtype={"naics_code": str})

    industry_shares = aggregate_sam_industry_shares(sam, commodity_shares)
    naics6, naics4, lookup_results, agg_grouped = distribute_to_naics_levels(
        industry_shares,
        bridge,
        agg_mapping,
        lookup_df,
    )

    industry_out = output_dir / "sam_auto_implan_shares.csv"
    naics6_out = output_dir / "sam_auto_naics6_shares.csv"
    naics4_out = output_dir / "sam_auto_naics4_mobility38.csv"
    agg_out = output_dir / "sam_auto_naics_aggregated_shares.csv"

    industry_shares.to_csv(industry_out, index=False)
    naics6.to_csv(naics6_out, index=False)
    lookup_results.to_csv(naics4_out, index=False)
    agg_grouped.to_csv(agg_out, index=False)

    print("Wrote SAM industry shares:", industry_out)
    print("Wrote NAICS6 shares:", naics6_out)
    print("Wrote NAICS4 mobility shares:", naics4_out)
    print("Wrote aggregated NAICS shares:", agg_out)


if __name__ == "__main__":
    main()
