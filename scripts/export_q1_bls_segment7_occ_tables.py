# -*- coding: utf-8 -*-
"""Export BLS segment 7 occupation highlights (level & percent change tables)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
OCC_PATH = (
    REPO_ROOT
    / "data/processed/sam_auto_dashboard_2025_Q1/sam_occ_segment_totals_2025_2034.csv"
)
OUTPUT_DIR = (
    REPO_ROOT
    / "data/processed/sam_auto_dashboard_2025_Q1/custom_table_output"
)
OUTPUT_PATH = OUTPUT_DIR / "bls_segment7_occ_highlights.xlsx"

SEGMENT_ID = 7
SEGMENT_NAME = "7. Core Automotive"
SCENARIO = "bls_us"
SCENARIO_LABEL = "BLS US"
BASE_YEAR = 2025
TARGET_YEAR = 2030
TABLE_LIMIT = 100

META_COLS = [
    "soctitle",
    "share",
    "share_2024",
    "share_2034",
    "ep_entry_education",
    "ep_work_experience",
    "ep_on_the_job_training",
    "ep_edu_grouped",
    "ep_edu_training_grouped",
    "ep_avg_annual_salary",
    "empl_2021",
]


def load_segment_data() -> tuple[pd.DataFrame, dict[str, float]]:
    df = pd.read_csv(OCC_PATH)
    scenario_df = df[df["projection_method"] == SCENARIO].copy()
    if scenario_df.empty:
        raise ValueError(f"No rows found for scenario '{SCENARIO}'.")
    mask = scenario_df["segment_id"] == SEGMENT_ID
    seg_df = scenario_df.loc[mask].copy()
    if seg_df.empty:
        raise ValueError(
            f"No rows found for segment {SEGMENT_ID} / {SEGMENT_NAME} "
            f"and scenario '{SCENARIO}'."
        )
    raw_lookup = (
        scenario_df[
            (scenario_df["segment_id"] == 0) & (scenario_df["year"] == BASE_YEAR)
        ]
        .set_index("occcd")["ep_openings_annual_avg"]
        .to_dict()
    )
    return seg_df, raw_lookup


def build_change_frame(df: pd.DataFrame, raw_lookup: dict[str, float]) -> pd.DataFrame:
    base = (
        df[df["year"] == BASE_YEAR]
        .copy()
        .set_index("occcd")
    )
    target = (
        df[df["year"] == TARGET_YEAR]
        .copy()
        .set_index("occcd")
    )
    shared = base.index.intersection(target.index)
    base = base.loc[shared]
    target = target.loc[shared]

    result = base[META_COLS].copy()
    result["segment_name"] = SEGMENT_NAME
    result["projection_label"] = SCENARIO_LABEL
    result["employment_auto_2025"] = base["employment_auto"].astype(float)
    result["employment_auto_2030"] = target["employment_auto"].astype(float)
    result["change_level"] = (
        result["employment_auto_2030"] - result["employment_auto_2025"]
    )
    result["change_percent"] = np.where(
        result["employment_auto_2025"] > 0,
        result["change_level"] / result["employment_auto_2025"],
        np.nan,
    )
    result["share_change"] = result["share_2034"] - result["share_2024"]
    result["occcd"] = base.index
    result["ep_openings_annual_avg"] = (
        result["occcd"].map(raw_lookup).fillna(0.0)
    )
    result["openings_auto"] = base["openings"].astype(float)
    result.reset_index(drop=True, inplace=True)
    # Ensure stable ordering of columns.
    ordered_cols = [
        "occcd",
        "soctitle",
        "segment_name",
        "projection_label",
        "employment_auto_2025",
        "employment_auto_2030",
        "change_level",
        "change_percent",
        "share",
        "share_2024",
        "share_2034",
        "share_change",
        "ep_openings_annual_avg",
        "openings_auto",
    ] + [
        c for c in META_COLS
        if c not in {"soctitle", "share", "share_2024", "share_2034", "ep_openings_annual_avg"}
    ]
    return result[ordered_cols]


def top_n(
    df: pd.DataFrame, column: str, ascending: bool, condition: str
) -> pd.DataFrame:
    filtered = df.copy()
    if condition == "positive":
        filtered = filtered[filtered[column] > 0]
    elif condition == "negative":
        filtered = filtered[filtered[column] < 0]
    filtered = filtered.sort_values(column, ascending=ascending)
    return filtered.head(TABLE_LIMIT)


def build_tables(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    tables: dict[str, pd.DataFrame] = {}
    tables["Top Level Increase"] = top_n(
        df, "change_level", ascending=False, condition="positive"
    )
    tables["Top Percent Increase"] = top_n(
        df, "change_percent", ascending=False, condition="positive"
    )
    tables["Top Level Decline"] = top_n(
        df, "change_level", ascending=True, condition="negative"
    )
    tables["Top Percent Decline"] = top_n(
        df, "change_percent", ascending=True, condition="negative"
    )
    tables["Top Share Increase"] = top_n(
        df, "share_change", ascending=False, condition="positive"
    )
    tables["Top Share Decline"] = top_n(
        df, "share_change", ascending=True, condition="negative"
    )
    tables["Top Avg Annual Openings"] = (
        df.sort_values("openings_auto", ascending=False)
        .head(TABLE_LIMIT)
        .copy()
    )
    tables["Top Avg Annual Openings"] = (
        df.sort_values("ep_openings_annual_avg", ascending=False)
        .head(TABLE_LIMIT)
        .copy()
    )
    return tables


def format_worksheets(writer: pd.ExcelWriter, tables: dict[str, pd.DataFrame]) -> None:
    workbook = writer.book
    percent_fmt = workbook.add_format({"num_format": "0.0%"})
    share_fmt = workbook.add_format({"num_format": "0.00%"})
    number_fmt = workbook.add_format({"num_format": "#,##0"})
    for sheet_name, table in tables.items():
        ws = writer.sheets[sheet_name]
        if table.empty:
            continue
        for idx, col in enumerate(table.columns, start=0):
            if col in {"employment_auto_2025", "employment_auto_2030", "change_level"}:
                ws.set_column(idx, idx, 16, number_fmt)
            elif col == "change_percent":
                ws.set_column(idx, idx, 14, percent_fmt)
            elif col in {"share", "share_2024", "share_2034", "share_change"}:
                ws.set_column(idx, idx, 14, share_fmt)
            elif col == "ep_openings_annual_avg":
                ws.set_column(idx, idx, 18, number_fmt)
            elif col in {"ep_openings_annual_avg", "openings_auto"}:
                ws.set_column(idx, idx, 18, number_fmt)
            else:
                ws.set_column(idx, idx, 18)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df, raw_lookup = load_segment_data()
    change_df = build_change_frame(df, raw_lookup)
    tables = build_tables(change_df)
    with pd.ExcelWriter(OUTPUT_PATH, engine="xlsxwriter") as writer:
        for sheet_name, table in tables.items():
            table.to_excel(writer, sheet_name=sheet_name, index=False)
        format_worksheets(writer, tables)
    print(f"Wrote BLS segment 7 occupation tables to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
