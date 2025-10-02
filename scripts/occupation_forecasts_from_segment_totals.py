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
        target = pd.DataFrame(columns=["segment_id", "occcd", "share_2034_bls"])

    shares = base.merge(target, on=["segment_id", "occcd"], how="left")
    shares["share_2034_bls"] = shares["share_2034_bls"].fillna(shares["share_2024"])

    records = []
    for _, row in shares.iterrows():
        seg_id = row["segment_id"]
        seg_name = row["segment_name"]
        occ = row["occcd"]
        title = row["soctitle"]
        edu = row["ep_edu_grouped"]
        entry = row["ep_entry_education"]
        work = row["ep_work_experience"]
        training = row["ep_on_the_job_training"]
        s0 = float(row["share_2024"])
        s1 = float(row["share_2034_bls"])

        for year in years:
            if year <= 2024:
                share = s0
            elif year >= 2034:
                share = s1
            else:
                t = (year - 2024) / (2034 - 2024)
                share = s0 + (s1 - s0) * t
            records.append({
                "segment_id": seg_id,
                "segment_name": seg_name,
                "occcd": occ,
                "soctitle": title,
                "year": year,
                "share": share,
                "share_2024": s0,
                "share_2034": s1,
                "ep_entry_education": entry,
                "ep_work_experience": work,
                "ep_on_the_job_training": training,
                "ep_edu_grouped": edu,
            })
    return pd.DataFrame(records)


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
    years = sorted(segment_totals["year"].unique())

    mcda = load_mcda_shares(args.mcda_path)
    us_shares = load_us_shares(args.us_summary_path)

    share_df = interpolate_shares(mcda, us_shares, years)

    forecasts = build_forecasts(segment_totals, share_df)
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
