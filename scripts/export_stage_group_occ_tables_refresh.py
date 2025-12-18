# -*- coding: utf-8 -*-
"""Export BLS occupation change tables for stage groupings."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
OCC_PATH = (
    REPO_ROOT
    / "data/processed/sam_auto_dashboard_2024_refresh/sam_occ_segment_totals_2024_2034.csv"
)
OUTPUT_DIR = (
    REPO_ROOT
    / "data/processed/sam_auto_dashboard_2024_refresh/custom_table_output"
)

SCENARIOS = {
    "bls_us": "BLS US",
    "dtmb_mi": "DTMB MI",
    "moodys_mi": "Moody's MI",
    "moodys_mi_detail": "Moody's MI detail",
    "moodys_us": "Moody's US",
}
BASE_YEAR = 2024
TARGET_YEAR = 2030
TOP_N = 100

STAGE_GROUPS = [
    {"key": "upstream", "label": "Upstream (segments 1-6)", "segments": set(range(1, 7))},
    {"key": "core_auto", "label": "Core Automotive (segment 7)", "segments": {7}},
    {"key": "downstream", "label": "Downstream (segments 8-10)", "segments": {8, 9, 10}},
    {"key": "upstream_core", "label": "Upstream + Core Automotive (segments 1-7)", "segments": set(range(1, 8))},
]

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
    "custom_training_group",
    "ep_avg_annual_salary",
    "empl_2021",
]

MODERATE_LONG_TRAINING = {
    "moderate-term on-the-job training",
    "long-term on-the-job training",
    "internship/residency",
    "apprenticeship",
}


def normalize_education(value: str | float | int | None) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "Unreported"
    text = str(value).strip().lower()
    if not text or text in {"nan", "none"}:
        return "Unreported"
    if "sc" in text or "associate" in text or "postsecondary" in text:
        return "SC or Associate's"
    if "hs" in text or "high school" in text:
        return "HS or Less"
    return "BA+"


def normalize_training(value: str | float | int | None) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ""
    return str(value).strip().lower()


def classify_custom_edu_training(row: pd.Series) -> str:
    """Recode education + training into four buckets."""
    edu_raw = str(row.get("ep_entry_education", "")).strip().lower()
    edu_grouped = normalize_education(row.get("ep_edu_grouped"))

    if any(token in edu_raw for token in ["bachelor", "master", "doctoral", "doctor", "professional", "ph.d", "phd"]):
        edu_class = "BA+"
    elif "associate" in edu_raw:
        edu_class = "Associate's"
    elif edu_grouped == "BA+":
        edu_class = "BA+"
    elif edu_grouped == "SC or Associate's":
        edu_class = "SC/HS"
    else:
        edu_class = "SC/HS"

    if edu_class == "BA+":
        return "BA+"
    if edu_class == "Associate's":
        return "Associate's"

    training_raw = row.get("ep_on_the_job_training")
    training_text = normalize_training(training_raw)
    if not training_text:
        training_text = normalize_training(row.get("ep_edu_training_grouped"))
    if training_text in MODERATE_LONG_TRAINING:
        return "HS/SC + moderate/long OJT"
    if training_text:
        return "HS/SC + no significant OJT"
    return "Other"


def load_occ_data() -> pd.DataFrame:
    df = pd.read_csv(OCC_PATH)
    return df


def build_stage_change_frame(
    df: pd.DataFrame,
    segments: set[int],
    stage_label: str,
    scenario_label: str,
    raw_openings_lookup: dict[str, float],
) -> pd.DataFrame:
    stage_df = df[df["segment_id"].isin(segments)].copy()
    if stage_df.empty:
        return pd.DataFrame()
    stage_df["custom_training_group"] = stage_df.apply(classify_custom_edu_training, axis=1)

    agg_dict = {
        "employment_auto": ("employment_auto", "sum"),
        "openings_auto": ("openings", "sum"),
    }
    for col in META_COLS:
        agg_dict[col] = (col, "first")
    agg = (
        stage_df.groupby(["occcd", "year"])
        .agg(**agg_dict)
        .reset_index()
    )

    base = agg[agg["year"] == BASE_YEAR].copy()
    target = agg[agg["year"] == TARGET_YEAR].copy()
    if base.empty or target.empty:
        return pd.DataFrame()

    base = base.drop(columns=["year"]).rename(columns={"employment_auto": "employment_auto_2024"})
    target = target.drop(columns=["year"]).rename(columns={"employment_auto": "employment_auto_2030"})

    merged = base.merge(
        target[["occcd", "employment_auto_2030"]],
        on="occcd",
        how="inner",
    )
    merged["segment_name"] = stage_label
    merged["projection_label"] = scenario_label
    merged["change_level"] = (
        merged["employment_auto_2030"] - merged["employment_auto_2024"]
    )
    merged["change_percent"] = np.where(
        merged["employment_auto_2024"] > 0,
        merged["change_level"] / merged["employment_auto_2024"],
        np.nan,
    )
    merged["share_change"] = merged["share_2034"] - merged["share_2024"]
    merged["ep_openings_annual_avg"] = (
        merged["occcd"].map(raw_openings_lookup).fillna(0.0)
    )
    ordered_cols = [
        "occcd",
        "soctitle",
        "segment_name",
        "projection_label",
        "employment_auto_2024",
        "employment_auto_2030",
        "change_level",
        "change_percent",
        "share",
        "share_2024",
        "share_2034",
        "share_change",
        "ep_openings_annual_avg",
        "openings_auto",
    ] + [col for col in META_COLS if col not in {"soctitle", "share", "share_2024", "share_2034"}]
    return merged[ordered_cols]


def top_n(df: pd.DataFrame, column: str, ascending: bool, sign: str) -> pd.DataFrame:
    table = df.copy()
    if sign == "positive":
        table = table[table[column] > 0]
    elif sign == "negative":
        table = table[table[column] < 0]
    table = table.sort_values(column, ascending=ascending)
    return table.head(TOP_N)


def build_tables(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    tables = {
        "Top Level Increase": top_n(df, "change_level", ascending=False, sign="positive"),
        "Top Percent Increase": top_n(df, "change_percent", ascending=False, sign="positive"),
        "Top Level Decline": top_n(df, "change_level", ascending=True, sign="negative"),
        "Top Percent Decline": top_n(df, "change_percent", ascending=True, sign="negative"),
        "Top Share Increase": top_n(df, "share_change", ascending=False, sign="positive"),
        "Top Share Decline": top_n(df, "share_change", ascending=True, sign="negative"),
    }
    tables["Top Avg Annual Openings"] = (
        df.sort_values("openings_auto", ascending=False)
        .head(TOP_N)
        .copy()
    )
    return tables


def format_sheet(writer: pd.ExcelWriter, tables: dict[str, pd.DataFrame]) -> None:
    workbook = writer.book
    num_fmt = workbook.add_format({"num_format": "#,##0"})
    pct_fmt = workbook.add_format({"num_format": "0.0%"})
    share_fmt = workbook.add_format({"num_format": "0.00%"})
    for sheet_name, table in tables.items():
        ws = writer.sheets[sheet_name]
        if table.empty:
            continue
        for idx, col in enumerate(table.columns):
            if col in {"employment_auto_2024", "employment_auto_2030", "change_level"}:
                ws.set_column(idx, idx, 16, num_fmt)
            elif col in {"change_percent"}:
                ws.set_column(idx, idx, 14, pct_fmt)
            elif col in {"share", "share_2024", "share_2034", "share_change"}:
                ws.set_column(idx, idx, 14, share_fmt)
            elif col in {"ep_openings_annual_avg", "openings_auto"}:
                ws.set_column(idx, idx, 18, num_fmt)
            else:
                ws.set_column(idx, idx, 18)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df = load_occ_data()
    for scenario_slug, scenario_label in SCENARIOS.items():
        scenario_df = df[df["projection_method"] == scenario_slug].copy()
        if scenario_df.empty:
            continue
        scenario_dir = OUTPUT_DIR / scenario_slug
        scenario_dir.mkdir(parents=True, exist_ok=True)
        raw_lookup = (
            scenario_df[
                (scenario_df["segment_id"] == 0) & (scenario_df["year"] == BASE_YEAR)
            ]
            .set_index("occcd")["ep_openings_annual_avg"]
            .to_dict()
        )
        for config in STAGE_GROUPS:
            summary = build_stage_change_frame(
                scenario_df,
                config["segments"],
                config["label"],
                scenario_label,
                raw_lookup,
            )
            if summary.empty:
                continue
            tables = build_tables(summary)
            output_path = scenario_dir / f"{scenario_slug}_stage_occ_highlights_{config['key']}.xlsx"
            with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
                for sheet_name, table in tables.items():
                    table.to_excel(writer, sheet_name=sheet_name, index=False)
                format_sheet(writer, tables)
            print(f"Wrote stage occupation tables to {output_path}")


if __name__ == "__main__":
    main()
