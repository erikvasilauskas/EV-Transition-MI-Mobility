"""Generate auto-attributed employment projection scenarios for all share/rate combinations."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


OEM_NAICS = {"5413", "5414", "5417"}

SHARE_METHODS = [
    ("sam_auto_share", "SAM (auto_share)", "sam"),
    ("lightcast_share", "Lightcast", "lightcast"),
    ("bea_summary_total_output_share", "BEA Summary (Total Output)", "bea_summary"),
    ("bea_detail_intermediate_share", "BEA Detail (Intermediate Inputs)", "bea_detail_inputs"),
    ("bea_detail_total_output_share", "BEA Detail (Total Output)", "bea_detail_output"),
    ("mrio_indirect_share", "MRIO Indirect", "mrio_indirect"),
    ("mrio_total_share", "MRIO Total", "mrio_total"),
]

PROJECTION_METHODS = [
    ("moodys_mi_pct_change_2024_2030_employment", "Moody's MI", "moodys_mi"),
    ("moodys_us_pct_change_2024_2030_employment", "Moody's US", "moodys_us"),
    ("mi_dtmb_six_year_rate", "DTMB MI", "dtmb_mi"),
    ("bls_us_six_year_employment_rate_change", "BLS US", "bls_us"),
]


def load_data(repo_root: Path) -> pd.DataFrame:
    share_path = repo_root / "data" / "intermediate" / "auto_share_comparison.csv"
    projection_path = repo_root / "data" / "intermediate" / "employment_projection_comparison.csv"

    shares = pd.read_csv(share_path, dtype={"naics_code": str})
    projections = pd.read_csv(projection_path, dtype={"naics_code": str})

    shares["naics_code"] = shares["naics_code"].str.strip().str.zfill(4)
    projections["naics_code"] = projections["naics_code"].str.strip().str.zfill(4)

    merged = shares.merge(
        projections[
            [
                "naics_code",
                "employment_qcew_2024",
                "moodys_mi_pct_change_2024_2030_employment",
                "moodys_us_pct_change_2024_2030_employment",
                "mi_dtmb_six_year_rate",
                "bls_us_six_year_employment_rate_change",
            ]
        ],
        on="naics_code",
        how="left",
        suffixes=("", "_proj"),
    )

    merged["employment_qcew_2024"] = merged["employment_qcew_2024"].fillna(merged["employment_qcew_2024_proj"])
    merged.drop(columns=["employment_qcew_2024_proj"], inplace=True)
    merged["employment_qcew_2024"] = merged["employment_qcew_2024"].fillna(0)
    merged["stage"] = merged["stage"].fillna("Unknown")
    merged["stage_lower"] = merged["stage"].str.lower()
    return merged


def apply_scenario(
    base_df: pd.DataFrame,
    share_col: str,
    share_label: str,
    share_slug: str,
    projection_col: str,
    projection_label: str,
    projection_slug: str,
) -> pd.DataFrame:
    df = base_df.copy()

    if share_col not in df.columns:
        df["share_value"] = 0.0
    else:
        df["share_value"] = df[share_col].fillna(0.0)

    if projection_col not in df.columns:
        df["projection_rate"] = 0.0
    else:
        df["projection_rate"] = df[projection_col].fillna(0.0)

    apply_mask = (df["stage_lower"] == "upstream") | (df["naics_code"].isin(OEM_NAICS))
    df["share_applied"] = np.where(apply_mask, df["share_value"], 1.0)

    df["base_employment"] = df["employment_qcew_2024"].fillna(0.0)
    df["auto_base_employment"] = np.round(df["base_employment"] * df["share_applied"]).astype(int)
    df["projected_employment"] = np.round(df["auto_base_employment"] * (1 + df["projection_rate"])).astype(int)

    df["share_method"] = share_slug
    df["share_label"] = share_label
    df["projection_method"] = projection_slug
    df["projection_label"] = projection_label

    cols = [
        "naics_code",
        "naics_title",
        "segment_id",
        "segment_name",
        "stage",
        "share_method",
        "share_label",
        "projection_method",
        "projection_label",
        "base_employment",
        "share_value",
        "share_applied",
        "auto_base_employment",
        "projection_rate",
        "projected_employment",
    ]
    return df[cols]


def summarize_segment(df: pd.DataFrame) -> pd.DataFrame:
    summary = (
        df.groupby(
            [
                "share_method",
                "share_label",
                "projection_method",
                "projection_label",
                "segment_id",
                "segment_name",
            ],
            as_index=False,
        )
        .agg(
            base_employment=("base_employment", "sum"),
            auto_base_employment=("auto_base_employment", "sum"),
            projected_employment=("projected_employment", "sum"),
        )
    )
    return summary


def summarize_stage(df: pd.DataFrame) -> pd.DataFrame:
    stage_summary = (
        df.groupby(
            [
                "share_method",
                "share_label",
                "projection_method",
                "projection_label",
                "stage",
            ],
            as_index=False,
        )
        .agg(
            base_employment=("base_employment", "sum"),
            auto_base_employment=("auto_base_employment", "sum"),
            projected_employment=("projected_employment", "sum"),
        )
    )

    uc_mask = df["stage"].str.lower().isin(["upstream", "core"])
    uc_totals = (
        df.loc[uc_mask]
        .groupby(
            ["share_method", "share_label", "projection_method", "projection_label"], as_index=False
        )
        .agg(
            base_employment=("base_employment", "sum"),
            auto_base_employment=("auto_base_employment", "sum"),
            projected_employment=("projected_employment", "sum"),
        )
    )
    uc_totals["stage"] = "Upstream+Core"

    combined = pd.concat([stage_summary, uc_totals], ignore_index=True)
    return combined


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    output_dir = repo_root / "data" / "processed" / "auto_employment_projections"
    naics_dir = output_dir / "naics"
    output_dir.mkdir(parents=True, exist_ok=True)
    naics_dir.mkdir(parents=True, exist_ok=True)

    base_df = load_data(repo_root)

    all_naics_rows = []
    all_segment_rows = []
    all_stage_rows = []

    for share_col, share_label, share_slug in SHARE_METHODS:
        for proj_col, proj_label, proj_slug in PROJECTION_METHODS:
            scenario_df = apply_scenario(
                base_df,
                share_col,
                share_label,
                share_slug,
                proj_col,
                proj_label,
                proj_slug,
            )

            scenario_file = naics_dir / f"naics_{share_slug}__{proj_slug}.csv"
            scenario_df.to_csv(scenario_file, index=False)

            all_naics_rows.append(scenario_df)
            all_segment_rows.append(summarize_segment(scenario_df))
            all_stage_rows.append(summarize_stage(scenario_df))

    naics_long = pd.concat(all_naics_rows, ignore_index=True)
    segment_summary = pd.concat(all_segment_rows, ignore_index=True)
    stage_summary = pd.concat(all_stage_rows, ignore_index=True)

    naics_long.to_csv(output_dir / "auto_employment_projection_naics_long.csv", index=False)
    segment_summary.to_csv(output_dir / "auto_employment_projection_segment_summary.csv", index=False)
    stage_summary.to_csv(output_dir / "auto_employment_projection_stage_summary.csv", index=False)

    print("Generated auto employment projection scenarios.")


if __name__ == "__main__":
    main()
