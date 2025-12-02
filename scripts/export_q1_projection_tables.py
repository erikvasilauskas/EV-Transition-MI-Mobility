# -*- coding: utf-8 -*-
"""Build Q1 segment & stage employment change tables."""

from __future__ import annotations

from pathlib import Path
import warnings

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_YEAR = 2025
TARGET_YEAR = 2030
SCENARIOS = {
    "moodys_mi_detail": "Moody's MI detail",
    "moodys_mi": "Moody's MI CAGR",
    "bls_us": "BLS US",
    "dtmb_mi": "DTMB MI",
}

SEGMENT_FILE = (
    REPO_ROOT
    / "data/processed/sam_auto_dashboard_2025_Q1/sam_employment_segment_timeseries.csv"
)
STAGE_FILE = (
    REPO_ROOT
    / "data/processed/sam_auto_dashboard_2025_Q1/sam_employment_stage_timeseries.csv"
)
OUTPUT_DIR = (
    REPO_ROOT
    / "data/processed/sam_auto_dashboard_2025_Q1"
    / "custom_table_output"
)


def build_projection_table(path: Path, entity_col: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = df[df["forecast_source"].isin(SCENARIOS.keys())].copy()
    df = df[df["year"].isin([BASE_YEAR, TARGET_YEAR])].copy()
    df[entity_col] = df[entity_col].astype(str)

    base_group = (
        df[df["year"] == BASE_YEAR]
        .groupby(entity_col)["employment_auto"]
    )
    baseline_min = base_group.min()
    baseline_max = base_group.max()
    diff = (baseline_max - baseline_min).abs()
    if (diff > 1e-6).any():
        warnings.warn(
            f"Multiple employment_auto baselines detected for {entity_col}; "
            "using the maximum (QCEW) value.",
            RuntimeWarning,
        )

    baseline_series = baseline_max
    baseline_df = (
        baseline_series.rename("employment_auto 2025")
        .reset_index()
        .sort_values(entity_col)
    )
    baseline_df.rename(columns={entity_col: "Entity"}, inplace=True)
    baseline_df.set_index("Entity", inplace=True)
    baseline_values = baseline_df["employment_auto 2025"]

    result = baseline_df.copy()

    for slug, label in SCENARIOS.items():
        target = df[
            (df["year"] == TARGET_YEAR)
            & (df["forecast_source"] == slug)
        ].set_index(entity_col)["employment_auto"]
        delta = target - baseline_values
        col_name = f"Δ employment_auto {label} 2025-2030"
        result[col_name] = result.index.map(delta)

    result.reset_index(inplace=True)
    ordered_columns = ["Entity", "employment_auto 2025"] + [
        f"Δ employment_auto {SCENARIOS[slug]} 2025-2030"
        for slug in SCENARIOS.keys()
    ]
    return result[ordered_columns]


def format_worksheet(
    writer: pd.ExcelWriter,
    sheet_name: str,
    data: pd.DataFrame,
) -> None:
    workbook = writer.book
    worksheet = writer.sheets[sheet_name]
    headers = list(data.columns)
    numeric_cols = {col for col in headers if col != "Entity"}
    n_rows = len(data)
    n_cols = len(headers)

    format_cache: dict[tuple, any] = {}

    def get_format(
        *,
        header: bool,
        numeric: bool,
        top: bool,
        bottom: bool,
        left: bool,
        right: bool,
    ):
        key = (header, numeric, top, bottom, left, right)
        if key not in format_cache:
            props: dict[str, object] = {"border": 1}
            if header:
                props.update({"bold": True, "bg_color": "#F2F2F2"})
            if numeric:
                props["num_format"] = "#,##0"
            if top:
                props["top"] = 2
            if bottom:
                props["bottom"] = 2
            if left:
                props["left"] = 2
            if right:
                props["right"] = 2
            format_cache[key] = workbook.add_format(props)
        return format_cache[key]

    for col, header_label in enumerate(headers):
        fmt = get_format(
            header=True,
            numeric=False,
            top=True,
            bottom=n_rows == 0,
            left=col == 0,
            right=col == n_cols - 1,
        )
        worksheet.write(0, col, header_label, fmt)
        width = 28 if col == 0 else 24 if col == 1 else 18
        worksheet.set_column(col, col, width)

    for row_idx, row in enumerate(data.itertuples(index=False), start=1):
        is_last = row_idx == n_rows
        for col_idx, header_label in enumerate(headers):
            value = row[col_idx]
            numeric = header_label in numeric_cols
            fmt = get_format(
                header=False,
                numeric=numeric,
                top=False,
                bottom=is_last,
                left=col_idx == 0,
                right=col_idx == n_cols - 1,
            )
            if numeric and pd.notna(value):
                worksheet.write_number(row_idx, col_idx, float(value), fmt)
            else:
                worksheet.write(
                    row_idx,
                    col_idx,
                    "" if pd.isna(value) else value,
                    fmt,
                )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    segment_table = build_projection_table(SEGMENT_FILE, "segment_name")
    stage_table = build_projection_table(STAGE_FILE, "stage")

    excel_path = OUTPUT_DIR / "segment_stage_projection_change.xlsx"
    with pd.ExcelWriter(excel_path, engine="xlsxwriter") as writer:
        segment_table.to_excel(writer, sheet_name="Segments", index=False)
        stage_table.to_excel(writer, sheet_name="Stages", index=False)
        format_worksheet(writer, "Segments", segment_table)
        format_worksheet(writer, "Stages", stage_table)

    print(f"Wrote projection tables to {excel_path}")


if __name__ == "__main__":
    main()
