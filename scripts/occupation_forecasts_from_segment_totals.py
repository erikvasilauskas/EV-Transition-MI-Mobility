# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

SEGMENT_LABELS = {
    1: "1. Materials & Processing",
    2: "2. Equipment Manufacturing",
    3: "3. Forging & Foundries",
    4: "4. Parts & Machining",
    5: "5. Component Systems",
    6: "6. Engineering & Design",
    7: "7. Core Automotive",
    8: "8. Motor Vehicle Parts, Materials, & Products Sales",
    9: "9. Dealers, Maintenance, & Repair",
    10: "10. Logistics",
}


def normalize_segment_totals(path: Path) -> pd.DataFrame:
    """Normalize segment totals compare file to long format."""
    df = pd.read_csv(path)

    required = {"segment_id", "segment_name", "year", "employment_qcew"}
    if not required.issubset(df.columns):
        missing = required - set(df.columns)
        raise ValueError(f"Segment totals file missing columns: {missing}")

    df["segment_id"] = pd.to_numeric(df["segment_id"], errors="coerce").astype("Int64")
    df["segment_name"] = df["segment_name"].astype(str).str.strip()
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype(int)
    df["employment_qcew"] = pd.to_numeric(df["employment_qcew"], errors="coerce")

    df["adjustment_source"] = df.get("adjustment_source", "").astype(str).str.strip().str.lower()
    df["forecast_source"] = df.get("forecast_source", "").astype(str).str.strip().str.lower()
    df.loc[df["forecast_source"] == "", "forecast_source"] = "qcew"
    df.loc[df["adjustment_source"] == "", "adjustment_source"] = "unadjusted"

    df["methodology"] = df["adjustment_source"] + "_" + df["forecast_source"]
    df["methodology"] = df["methodology"].str.replace("__", "_", regex=False)

    df = df[(df["year"] >= 2024) & (df["year"] <= 2034)]
    df = df[df["employment_qcew"].notna()]

    return df[["segment_id", "segment_name", "year", "methodology", "employment_qcew"]]



def expand_base_year_methods(segment_totals: pd.DataFrame) -> pd.DataFrame:
    """Duplicate base-year rows across forecast methodologies."""
    if segment_totals.empty:
        return segment_totals

    base_year = int(segment_totals["year"].min())

    future_methods = (
        segment_totals[segment_totals["year"] > base_year]["methodology"]
        .dropna()
        .unique()
    )

    prefix_map: dict[str, set[str]] = {}
    for method in future_methods:
        method_str = str(method)
        if not method_str:
            continue
        prefix = method_str.split("_")[0]
        prefix_map.setdefault(prefix, set()).add(method_str)

    base_rows = segment_totals[segment_totals["year"] == base_year].copy()
    if base_rows.empty:
        return segment_totals

    expanded_rows: list[pd.Series] = []
    for _, row in base_rows.iterrows():
        method_str = str(row["methodology"])
        prefix = method_str.split("_")[0]
        target_methods = sorted(prefix_map.get(prefix, []))
        if not target_methods:
            target_methods = [method_str]
        for target_method in target_methods:
            new_row = row.copy()
            new_row["methodology"] = target_method
            expanded_rows.append(new_row)

    if not expanded_rows:
        return segment_totals

    expanded_df = pd.DataFrame(expanded_rows)
    remainder = segment_totals[segment_totals["year"] > base_year]
    combined = pd.concat([expanded_df, remainder], ignore_index=True)
    combined = combined.sort_values(["segment_id", "year", "methodology"]).reset_index(drop=True)
    return combined



def load_mcda_shares(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)

    if "segment_id" in df.columns:
        df["segment_id"] = pd.to_numeric(df["segment_id"], errors="coerce").astype("Int64")
    elif "segment" in df.columns:
        df["segment_id"] = (
            df["segment"].astype(str).str.extract(r"^(\d+)")[0].astype(float).astype("Int64")
        )
    else:
        raise ValueError("MCDA staffing file must include either 'segment_id' or 'segment'.")

    df["segment_name"] = df.get("segment", df["segment_id"].map(SEGMENT_LABELS))
    df["segment_name"] = df["segment_name"].astype(str).str.strip()

    if "occ_level" in df.columns:
        df = df[df["occ_level"].str.lower() == "detailed"].copy()
    if "year" in df.columns:
        df = df[df["year"] == 2024].copy()

    if "pct_seg_detailed_2024" in df.columns:
        df["share_2024"] = pd.to_numeric(df["pct_seg_detailed_2024"], errors="coerce")
    else:
        if "empl_2024" not in df.columns:
            raise ValueError("MCDA staffing file must contain pct_seg_detailed_2024 or empl_2024")
        df["empl_2024"] = pd.to_numeric(df["empl_2024"], errors="coerce")
        totals = df.groupby("segment_id")["empl_2024"].transform("sum")
        df["share_2024"] = np.where(totals > 0, df["empl_2024"] / totals, np.nan)

    df = df[df["share_2024"].notna()].copy()
    df["occcd"] = df["occcd"].astype(str).str.strip()

    keep_cols = [
        "segment_id",
        "segment_name",
        "occcd",
        "soctitle",
        "share_2024",
        "ep_entry_education",
        "ep_work_experience",
        "ep_on_the_job_training",
        "ep_edu_grouped",
    ]
    for col in keep_cols:
        if col not in df.columns:
            df[col] = np.nan
    return df[keep_cols]


def load_us_shares(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["segment_id"] = pd.to_numeric(df["segment_id"], errors="coerce").astype("Int64")
    df["Occupation Code"] = df["Occupation Code"].astype(str).str.strip()
    df = df[~df["Occupation Code"].str.endswith("-0000")].copy()
    df = df.rename(columns={
        "Occupation Code": "occcd",
        "segment_share_2024": "share_2024_bls",
        "segment_share_2034": "share_2034_bls",
    })
    return df[["segment_id", "occcd", "share_2024_bls", "share_2034_bls"]]



def interpolate_shares(base: pd.DataFrame, target: Optional[pd.DataFrame], years: list[int]) -> pd.DataFrame:
    if target is None:
        target = pd.DataFrame(columns=["segment_id", "occcd", "share_2024_bls", "share_2034_bls"])

    shares = base.merge(target, on=["segment_id", "occcd"], how="left")

    shares["share_2024"] = pd.to_numeric(shares["share_2024"], errors="coerce").fillna(0.0)

    if "share_2024_bls" in shares.columns:
        shares["share_2024_bls"] = pd.to_numeric(shares["share_2024_bls"], errors="coerce")
    else:
        shares["share_2024_bls"] = np.nan
    if "share_2034_bls" in shares.columns:
        shares["share_2034_bls"] = pd.to_numeric(shares["share_2034_bls"], errors="coerce")
    else:
        shares["share_2034_bls"] = np.nan

    base_totals = shares.groupby("segment_id")["share_2024"].transform("sum")
    shares["base_share"] = shares["share_2024"] / base_totals
    shares["base_share"] = shares["base_share"].fillna(0.0)

    shares["share_2024_bls"] = shares["share_2024_bls"].fillna(shares["share_2034_bls"])
    shares["share_2024_bls"] = shares["share_2024_bls"].fillna(shares["base_share"])
    shares["share_2034_bls"] = shares["share_2034_bls"].fillna(shares["share_2024_bls"])

    shares["growth_factor"] = 1.0
    mask = shares["share_2024_bls"] > 0
    shares.loc[mask, "growth_factor"] = shares.loc[mask, "share_2034_bls"] / shares.loc[mask, "share_2024_bls"]
    shares["growth_factor"] = shares["growth_factor"].replace([np.inf, -np.inf], 1.0).fillna(1.0)

    shares["target_share_raw"] = shares["base_share"] * shares["growth_factor"]
    target_totals = shares.groupby("segment_id")["target_share_raw"].transform("sum")
    shares["target_share"] = shares["target_share_raw"] / target_totals
    shares["target_share"] = shares["target_share"].replace([np.inf, -np.inf], np.nan).fillna(shares["base_share"])
    shares = shares.drop(columns=["target_share_raw"])

    results = []
    result_cols = [
        "segment_id",
        "segment_name",
        "occcd",
        "soctitle",
        "year",
        "share",
        "share_2024",
        "share_2034",
        "ep_entry_education",
        "ep_work_experience",
        "ep_on_the_job_training",
        "ep_edu_grouped",
    ]

    for year in years:
        if year <= 2024:
            progress = 0.0
        elif year >= 2034:
            progress = 1.0
        else:
            progress = (year - 2024) / (2034 - 2024)

        temp = shares.copy()
        temp["share"] = temp["base_share"] * (1 + (temp["growth_factor"] - 1) * progress)
        totals = temp.groupby("segment_id")["share"].transform("sum")
        temp["share"] = temp["share"] / totals
        temp["share"] = temp["share"].replace([np.inf, -np.inf], np.nan).fillna(temp["base_share"])

        temp["year"] = int(year)
        temp["share_2024"] = temp["base_share"]
        temp["share_2034"] = temp["target_share"]

        results.append(temp[result_cols])

    if not results:
        return pd.DataFrame(columns=result_cols)

    return pd.concat(results, ignore_index=True)


def build_forecasts(segment_totals: pd.DataFrame, share_df: pd.DataFrame) -> pd.DataFrame:
    totals = segment_totals.set_index(["segment_id", "year", "methodology"])  # type: ignore[arg-type]
    records = []
    methodologies = segment_totals["methodology"].unique()

    for _, row in share_df.iterrows():
        seg_id = row["segment_id"]
        year = row["year"]
        share = row["share"]
        for method in methodologies:
            key = (seg_id, year, method)
            if key not in totals.index:
                continue
            total = totals.loc[key, "employment_qcew"]
            employment = total * share
            records.append({
                "segment_id": seg_id,
                "segment_name": row["segment_name"],
                "year": year,
                "methodology": method,
                "occcd": row["occcd"],
                "soctitle": row["soctitle"],
                "employment": employment,
                "share": share,
                "share_2024": row["share_2024"],
                "share_2034": row["share_2034"],
                "ep_entry_education": row["ep_entry_education"],
                "ep_work_experience": row["ep_work_experience"],
                "ep_on_the_job_training": row["ep_on_the_job_training"],
                "ep_edu_grouped": row["ep_edu_grouped"],
            })
    return pd.DataFrame(records)


def main() -> None:
    parser = argparse.ArgumentParser(description="Create occupation forecasts from segment totals.")
    parser.add_argument("--compare-path", type=Path, default=Path("data/processed/mi_qcew_segment_employment_timeseries_lightcast_vs_bea_compare.csv"))
    parser.add_argument("--mcda-path", type=Path, default=Path("data/processed/mcda_staffing_detailed_2021_2024.csv"))
    parser.add_argument("--us-summary-path", type=Path, default=Path("data/processed/us_staffing_segments_summary.csv"))
    parser.add_argument("--out-prefix", type=str, default="mi_occ_segment_totals")
    args = parser.parse_args()

    segment_totals = normalize_segment_totals(args.compare_path)
    segment_totals = expand_base_year_methods(segment_totals)
    years = sorted(segment_totals["year"].unique())
    base_year = years[0]
    target_year = years[-1]

    mcda = load_mcda_shares(args.mcda_path)
    us_shares = load_us_shares(args.us_summary_path)


    share_df = interpolate_shares(mcda, us_shares, years)

    forecasts = build_forecasts(segment_totals, share_df)

    # Append aggregated totals across all segments as segment 0
    segment_meta_cols = [
        "occcd",
        "soctitle",
        "methodology",
        "year",
        "ep_entry_education",
        "ep_work_experience",
        "ep_on_the_job_training",
        "ep_edu_grouped",
    ]
    aggregated = forecasts.groupby(segment_meta_cols, as_index=False)["employment"].sum()
    aggregated["segment_id"] = 0
    aggregated["segment_name"] = "0. All Segments"

    year_group_totals = aggregated.groupby(["methodology", "year"])["employment"].transform("sum")
    aggregated["share"] = np.where(year_group_totals > 0, aggregated["employment"] / year_group_totals, np.nan)

    share_lookup = forecasts[["methodology", "occcd", "share_2024", "share_2034"]].drop_duplicates(subset=["methodology", "occcd"])
    aggregated = aggregated.merge(share_lookup, on=["methodology", "occcd"], how="left")

    aggregated = aggregated[[
        "segment_id",
        "segment_name",
        "year",
        "methodology",
        "occcd",
        "soctitle",
        "employment",
        "share",
        "share_2024",
        "share_2034",
        "ep_entry_education",
        "ep_work_experience",
        "ep_on_the_job_training",
        "ep_edu_grouped",
    ]]

    forecasts = pd.concat([forecasts, aggregated], ignore_index=True)
    forecasts = forecasts.sort_values(["segment_id", "occcd", "year", "methodology"])

    out_dir = Path("data/processed")
    out_dir.mkdir(parents=True, exist_ok=True)

    full_path = out_dir / f"{args.out_prefix}_2024_2034.csv"
    forecasts.to_csv(full_path, index=False)

    snap_2030 = forecasts[forecasts["year"] == 2030].copy()
    snap_path = out_dir / f"{args.out_prefix}_2030.csv"
    snap_2030.to_csv(snap_path, index=False)

    occ_totals = forecasts.groupby(["segment_id", "year", "methodology"], as_index=False)["employment"].sum()
    validation = occ_totals.merge(segment_totals, on=["segment_id", "year", "methodology"], how="left")
    validation["pct_diff"] = np.where(
        validation["employment_qcew"] > 0,
        (validation["employment"] - validation["employment_qcew"]) / validation["employment_qcew"] * 100,
        np.nan,
    )
    val_path = out_dir / f"{args.out_prefix}_validation.csv"
    validation.to_csv(val_path, index=False)

    print("Saved forecasts:", full_path)
    print("Saved 2030 snapshot:", snap_path)
    print("Saved validation:", val_path)


if __name__ == "__main__":
    main()
