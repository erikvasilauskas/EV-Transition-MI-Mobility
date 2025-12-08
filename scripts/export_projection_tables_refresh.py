"""Build segment and stage employment change tables for the refreshed 2024 dashboard run."""

from __future__ import annotations

from pathlib import Path
import warnings

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_YEAR = 2024
TARGET_YEAR = 2030
SCENARIOS = {
    "moodys_mi_detail": "Moody's MI detail",
    "moodys_mi": "Moody's MI CAGR",
    "bls_us": "BLS US",
    "dtmb_mi": "DTMB MI",
}

SEGMENT_FILE = REPO_ROOT / "data/processed/sam_auto_dashboard_2024_refresh/sam_employment_segment_timeseries.csv"
STAGE_FILE = REPO_ROOT / "data/processed/sam_auto_dashboard_2024_refresh/sam_employment_stage_timeseries.csv"
OUTPUT_DIR = REPO_ROOT / "data/processed/sam_auto_dashboard_2024_refresh" / "custom_table_output"


def build_projection_table(path: Path, entity_col: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = df[df["forecast_source"].isin(SCENARIOS.keys())].copy()
    df = df[df["year"].isin([BASE_YEAR, TARGET_YEAR])].copy()
    df[entity_col] = df[entity_col].astype(str)

    base_group = df[df["year"] == BASE_YEAR].groupby(entity_col)["employment_auto"]
    baseline_min = base_group.min()
    baseline_max = base_group.max()
    diff = (baseline_max - baseline_min).abs()
    if (diff > 1e-6).any():
        warnings.warn(
            f"Multiple employment_auto baselines detected for {entity_col}; using the maximum (QCEW) value.",
            RuntimeWarning,
        )

    baseline_col = f"employment_auto {BASE_YEAR}"
    baseline_df = (
        baseline_max.rename(baseline_col)
        .reset_index()
        .sort_values(entity_col)
        .rename(columns={entity_col: "Entity"})
        .set_index("Entity")
    )
    baseline_values = baseline_df[baseline_col]

    result = baseline_df.copy()
    for slug, label in SCENARIOS.items():
        target = (
            df[(df["year"] == TARGET_YEAR) & (df["forecast_source"] == slug)]
            .set_index(entity_col)["employment_auto"]
        )
        delta = target - baseline_values
        col_name = f"Delta employment_auto {label} {BASE_YEAR}-{TARGET_YEAR}"
        result[col_name] = result.index.map(delta)

    result.reset_index(inplace=True)
    ordered_columns = ["Entity", baseline_col] + [
        f"Delta employment_auto {SCENARIOS[slug]} {BASE_YEAR}-{TARGET_YEAR}" for slug in SCENARIOS
    ]
    return result[ordered_columns]


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    segment_table = build_projection_table(SEGMENT_FILE, "segment_name")
    stage_table = build_projection_table(STAGE_FILE, "stage_clean")

    csv_segment = OUTPUT_DIR / "projection_segment_change_2024_2030.csv"
    csv_stage = OUTPUT_DIR / "projection_stage_change_2024_2030.csv"
    xlsx_path = OUTPUT_DIR / "projection_change_tables_2024.xlsx"

    segment_table.to_csv(csv_segment, index=False)
    stage_table.to_csv(csv_stage, index=False)

    with pd.ExcelWriter(xlsx_path, engine="xlsxwriter") as writer:
        segment_table.to_excel(writer, sheet_name="Segments", index=False)
        stage_table.to_excel(writer, sheet_name="Stages", index=False)

    print("Wrote projection change tables:")
    print(f"  {csv_segment}")
    print(f"  {csv_stage}")
    print(f"  {xlsx_path}")


if __name__ == "__main__":
    main()
