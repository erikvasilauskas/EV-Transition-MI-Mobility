from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from process_moodys_time_series import read_wide

REPO_ROOT = Path(__file__).resolve().parents[1]
SAM_AUTOSHARE_PATH = REPO_ROOT / "data" / "intermediate" / "sam_naics_shares_v2" / "sam_auto_naics4_mobility38.csv"
OUTPUT_DIR = REPO_ROOT / "data" / "processed" / "sam_auto_dashboard"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_sam_meta() -> pd.DataFrame:
    df = pd.read_csv(SAM_AUTOSHARE_PATH, dtype={"naics_code": str})
    df["naics_code"] = df["naics_code"].str.strip().str.zfill(4)
    df["stage"] = df["stage"].astype(str).str.strip()
    df["segment_name"] = df["segment_name"].astype(str).str.strip()
    df["segment_subgroup"] = df.get("segment", df["segment_name"])
    return df


def load_moodys_employment() -> pd.DataFrame:
    df, year_cols = read_wide()
    geo_df = df[(df["Geography:"].astype(str).str.strip() == "Michigan") & (df["metric"] == "employment")].copy()
    geo_df["naics_code"] = geo_df["naics_code"].astype(str)
    long_df = geo_df.melt(
        id_vars=["naics_code", "Description:"],
        value_vars=year_cols,
        var_name="year",
        value_name="employment",
    )
    long_df["year"] = pd.to_datetime(long_df["year"], errors="coerce").dt.year
    long_df = long_df.dropna(subset=["year"])
    long_df["employment"] = pd.to_numeric(long_df["employment"], errors="coerce")
    long_df = long_df.dropna(subset=["employment"])
    long_df.rename(columns={"Description:": "description"}, inplace=True)
    return long_df


def build_naics_timeseries(moodys_df: pd.DataFrame, sam_meta: pd.DataFrame) -> pd.DataFrame:
    target_years = [year for year in sorted(moodys_df["year"].unique()) if 2001 <= year <= 2034]
    filtered = moodys_df[moodys_df["year"].isin(target_years)].copy()
    filtered["naics_code"] = filtered["naics_code"].str.zfill(4)

    merged = filtered.merge(
        sam_meta,
        on="naics_code",
        how="inner",
        suffixes=("", "_sam"),
    )
    merged["auto_share_of_output"] = merged["auto_share_of_output"].fillna(1.0)
    merged["employment_auto"] = merged["employment"] * merged["auto_share_of_output"]
    merged.rename(columns={"segment": "segment_label"}, inplace=True)

    merged[
        "projection_method"
    ] = "moodys_mi_detail"
    merged["projection_label"] = "Moody's MI (detail)"
    merged["value_type"] = "Moody's detailed"
    merged["projection_rate_total"] = np.nan
    merged["projection_cagr"] = np.nan
    return merged[
        [
            "projection_method",
            "projection_label",
            "naics_code",
            "naics_title",
            "segment_id",
            "segment_name",
            "segment_subgroup",
            "stage",
            "year",
            "value_type",
            "auto_share_of_output",
            "employment_auto",
            "employment",
            "projection_rate_total",
            "projection_cagr",
        ]
    ]


def aggregate_segments(naics_ts: pd.DataFrame) -> pd.DataFrame:
    agg = (
        naics_ts
        .groupby(
            [
                "projection_method",
                "projection_label",
                "year",
                "segment_id",
                "segment_name",
                "value_type",
            ],
            as_index=False,
        )
        [["employment", "employment_auto"]]
        .sum()
    )
    agg.rename(columns={"employment": "employment_raw"}, inplace=True)
    agg["auto_share_ratio"] = np.where(
        agg["employment_raw"] > 0,
        agg["employment_auto"] / agg["employment_raw"],
        np.nan,
    )
    return agg


def aggregate_stages(naics_ts: pd.DataFrame) -> pd.DataFrame:
    agg = (
        naics_ts
        .groupby(
            [
                "projection_method",
                "projection_label",
                "year",
                "value_type",
                "stage",
            ],
            as_index=False,
        )
        [["employment", "employment_auto"]]
        .sum()
    )
    agg.rename(columns={"employment": "employment_raw"}, inplace=True)
    agg["auto_share_ratio"] = np.where(
        agg["employment_raw"] > 0,
        agg["employment_auto"] / agg["employment_raw"],
        np.nan,
    )
    uc = (
        agg[agg["stage"].str.lower().isin(["upstream", "oem"])]
        .groupby([
            "projection_method",
            "projection_label",
            "year",
            "value_type",
        ], as_index=False)[["employment_raw", "employment_auto"]]
        .sum()
    )
    uc["stage"] = "Upstream+Core"
    uc["auto_share_ratio"] = np.where(
        uc["employment_raw"] > 0,
        uc["employment_auto"] / uc["employment_raw"],
        np.nan,
    )
    return pd.concat([agg, uc], ignore_index=True)


def main() -> None:
    sam_meta = load_sam_meta()
    moodys_df = load_moodys_employment()
    naics_ts = build_naics_timeseries(moodys_df, sam_meta)
    segment_ts = aggregate_segments(naics_ts)
    stage_ts = aggregate_stages(naics_ts)

    naics_path = OUTPUT_DIR / "moodys_mi_employment_naics_timeseries.csv"
    segment_path = OUTPUT_DIR / "moodys_mi_employment_segment_timeseries.csv"
    stage_path = OUTPUT_DIR / "moodys_mi_employment_stage_timeseries.csv"

    naics_ts.to_csv(naics_path, index=False)
    segment_ts.to_csv(segment_path, index=False)
    stage_ts.to_csv(stage_path, index=False)
    print("Saved:")
    print(f" - {naics_path}")
    print(f" - {segment_path}")
    print(f" - {stage_path}")


if __name__ == "__main__":
    main()




