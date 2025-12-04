"""Summarize occupation employment change by education/training group (2025-2030).

This mirrors `analyze_occ_change_by_education_q1.py` but uses the
`ep_edu_training_grouped` classification. Outputs go to a subdirectory of
the Q1 custom tables.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


BASE_YEAR = 2025
TARGET_YEAR = 2030
METHODOLOGY = "sam_mi_moodys_mi"
PROJECTION_METHOD = "moodys_mi"

SEGMENT_FILE = Path("data/processed/sam_auto_dashboard_2025_Q1/sam_occ_segment_totals_2025_2034.csv")
SEGMENT_TIMESERIES_FILE = Path("data/processed/sam_auto_dashboard_2025_Q1/sam_employment_segment_timeseries.csv")
OUTPUT_DIR = Path(
    "data/processed/sam_auto_dashboard_2025_Q1/custom_table_output/occ_change_by_education_2025_2030/training"
)

STAGE_GROUPS = [
    {"key": "upstream", "name": "Upstream", "label": "Upstream (segments 1-5)", "segments": set(range(1, 6))},
    {"key": "core_oem", "name": "Core/OEM", "label": "Core/OEM (segments 6-7)", "segments": {6, 7}},
    {"key": "downstream", "name": "Downstream", "label": "Downstream (segments 8-10)", "segments": {8, 9, 10}},
    {"key": "upstream_core", "name": "Upstream + Core/OEM", "label": "Upstream + Core/OEM (segments 1-7)", "segments": set(range(1, 8))},
    {"key": "all_segments", "name": "All Segments", "label": "All Segments (segments 1-10)", "segments": set(range(1, 11))},
]


def normalize_training(value: str | float | int | None) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "Unreported"
    text = str(value).strip()
    return text if text else "Unreported"


def load_segment_panel(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_csv(path)
    df = df[
        (df["year"].isin({BASE_YEAR, TARGET_YEAR}))
        & (df["methodology"] == METHODOLOGY)
        & (df["projection_method"] == PROJECTION_METHOD)
    ].copy()
    if df.empty:
        raise ValueError("No rows after filtering for methodology/projection.")
    df["segment_id"] = pd.to_numeric(df["segment_id"], errors="coerce").astype("Int64")
    df = df.dropna(subset=["segment_id"])
    df["segment_id"] = df["segment_id"].astype(int)
    df = df[df["segment_id"] > 0]
    df["training_group"] = df.get("ep_edu_training_grouped", "").apply(normalize_training)
    df["segment_name"] = df["segment_name"].astype(str)
    return df


def load_segment_shares(year: int) -> tuple[dict[int, float], dict[int, float]]:
    if not SEGMENT_TIMESERIES_FILE.exists():
        raise FileNotFoundError(SEGMENT_TIMESERIES_FILE)
    seg = pd.read_csv(SEGMENT_TIMESERIES_FILE)
    seg = seg[(seg["year"] == year) & seg["segment_id"].notna()].copy()
    seg["segment_id"] = seg["segment_id"].astype(int)
    seg["share_ratio"] = np.where(
        seg["employment_raw"].fillna(0.0) > 0,
        seg["employment_auto"].fillna(0.0) / seg["employment_raw"].replace(0, np.nan),
        1.0,
    )
    seg["share_ratio"] = seg["share_ratio"].replace([np.inf, -np.inf], np.nan).fillna(1.0)
    share_map = seg.set_index("segment_id")["share_ratio"].to_dict()
    auto_totals = seg.set_index("segment_id")["employment_auto"].to_dict()
    return share_map, auto_totals


def aggregate_segment_year_totals(df: pd.DataFrame, value_col: str) -> pd.DataFrame:
    group_cols = [
        "segment_id",
        "segment_name",
        "training_group",
        "year",
    ]
    grouped = df.groupby(group_cols, as_index=False)[value_col].sum()
    return grouped.rename(columns={value_col: "employment"})


def compute_change(grouped: pd.DataFrame, share_map: dict[int, float]) -> pd.DataFrame:
    base = grouped[grouped["year"] == BASE_YEAR].rename(columns={"employment": "employment_base"}).drop(columns="year")
    target = grouped[grouped["year"] == TARGET_YEAR].rename(
        columns={"employment": "employment_target"}
    ).drop(columns="year")
    merged = base.merge(target, on=["segment_id", "segment_name", "training_group"], how="outer").fillna(0.0)
    merged["employment_base_auto_adj"] = merged["employment_base"] * merged["segment_id"].map(share_map).fillna(1.0)
    merged["employment_target_auto_adj"] = merged["employment_target"] * merged["segment_id"].map(share_map).fillna(1.0)
    merged["employment_change"] = merged["employment_target_auto_adj"] - merged["employment_base_auto_adj"]
    merged["pct_change"] = np.where(
        merged["employment_base_auto_adj"] != 0,
        merged["employment_change"] / merged["employment_base_auto_adj"],
        np.nan,
    )
    return merged[
        [
            "segment_id",
            "segment_name",
            "training_group",
            "employment_base_auto_adj",
            "employment_target_auto_adj",
            "employment_change",
            "pct_change",
        ]
    ]


def aggregate_stage_totals(df: pd.DataFrame, share_map: dict[int, float]) -> pd.DataFrame:
    records: list[dict[str, object]] = []
    for group in STAGE_GROUPS:
        seg_ids = group["segments"]
        subset = df[df["segment_id"].isin(seg_ids)].copy()
        if subset.empty:
            continue
        subset["share_ratio"] = subset["segment_id"].map(share_map).fillna(1.0)
        subset["employment_auto_adj"] = subset["employment"] * subset["share_ratio"]
        grouped = subset.groupby(["training_group", "year"], as_index=False)["employment_auto_adj"].sum()
        base = grouped[grouped["year"] == BASE_YEAR].rename(columns={"employment_auto_adj": "employment_base"})
        target = grouped[grouped["year"] == TARGET_YEAR].rename(columns={"employment_auto_adj": "employment_target"})
        merged = base.merge(target, on="training_group", how="outer").fillna(0.0)
        merged["employment_change"] = merged["employment_target"] - merged["employment_base"]
        merged["pct_change"] = np.where(
            merged["employment_base"] != 0,
            merged["employment_change"] / merged["employment_base"],
            np.nan,
        )
        for _, row in merged.iterrows():
            records.append(
                {
                    "stage_key": group["key"],
                    "stage_label": group["label"],
                    "training_group": row["training_group"],
                    "employment_base": row["employment_base"],
                    "employment_target": row["employment_target"],
                    "employment_change": row["employment_change"],
                    "pct_change": row["pct_change"],
                }
            )
    return pd.DataFrame.from_records(records)


def aggregate_total(df: pd.DataFrame, share_map: dict[int, float]) -> pd.DataFrame:
    subset = df.copy()
    subset["share_ratio"] = subset["segment_id"].map(share_map).fillna(1.0)
    subset["employment_auto_adj"] = subset["employment"] * subset["share_ratio"]
    grouped = subset.groupby(["training_group", "year"], as_index=False)["employment_auto_adj"].sum()
    base = grouped[grouped["year"] == BASE_YEAR].rename(columns={"employment_auto_adj": "employment_base"})
    target = grouped[grouped["year"] == TARGET_YEAR].rename(columns={"employment_auto_adj": "employment_target"})
    merged = base.merge(target, on="training_group", how="outer").fillna(0.0)
    merged["employment_change"] = merged["employment_target"] - merged["employment_base"]
    merged["pct_change"] = np.where(
        merged["employment_base"] != 0,
        merged["employment_change"] / merged["employment_base"],
        np.nan,
    )
    merged["stage_key"] = "all_segments"
    merged["stage_label"] = "All Segments"
    return merged[
        [
            "stage_key",
            "stage_label",
            "training_group",
            "employment_base",
            "employment_target",
            "employment_change",
            "pct_change",
        ]
    ]


def write_outputs(segment_df: pd.DataFrame, stage_df: pd.DataFrame, total_df: pd.DataFrame) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    seg_path = OUTPUT_DIR / "segment_occ_change_by_training_2025_2030.csv"
    stage_path = OUTPUT_DIR / "stage_occ_change_by_training_2025_2030.csv"
    total_path = OUTPUT_DIR / "total_occ_change_by_training_2025_2030.csv"
    segment_df.to_csv(seg_path, index=False)
    stage_df.to_csv(stage_path, index=False)
    total_df.to_csv(total_path, index=False)

    with pd.ExcelWriter(OUTPUT_DIR / "occ_change_by_training_2025_2030.xlsx", engine="xlsxwriter") as writer:
        segment_df.to_excel(writer, sheet_name="segments", index=False)
        stage_df.to_excel(writer, sheet_name="stages", index=False)
        total_df.to_excel(writer, sheet_name="total", index=False)


def main() -> None:
    df = load_segment_panel(SEGMENT_FILE)
    share_map, _ = load_segment_shares(BASE_YEAR)

    seg_grouped = aggregate_segment_year_totals(df, "employment_auto")
    seg_change = compute_change(seg_grouped, share_map)

    stage_change = aggregate_stage_totals(df, share_map)
    total_change = aggregate_total(df, share_map)

    write_outputs(seg_change, stage_change, total_change)
    print(f"Wrote training change tables to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
