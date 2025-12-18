# -*- coding: utf-8 -*-
"""Build nested stage/segment/NAICS employment change tables for multiple scenarios (2024→2030)."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data" / "processed" / "sam_auto_dashboard_2024_refresh"
NAICS_TS_PATH = DATA_DIR / "sam_employment_naics_timeseries.csv"
SEG_TS_PATH = DATA_DIR / "sam_employment_segment_timeseries.csv"
STAGE_TS_PATH = DATA_DIR / "sam_employment_stage_timeseries.csv"
OUT_PATH = DATA_DIR / "custom_table_output" / "stage_segment_naics_employment_change_2024_2030.xlsx"

BASE_YEAR = 2024
TARGET_YEAR = 2030
YEARS = (BASE_YEAR, TARGET_YEAR)

SCENARIOS = {
    "moodys_mi": "Moody's MI",
    "dtmb_mi": "DTMB MI",
    "bls_us": "BLS US",
}

STAGE_ORDER = ["upstream", "core automotive", "downstream"]
STAGE_LABELS = {
    "upstream": "Upstream",
    "core automotive": "Core Automotive",
    "oem": "Core Automotive",
    "upstream + core automotive": "Upstream + Core Automotive",
    "downstream": "Downstream",
}


def load_timeseries(path: Path, years: tuple[int, int]) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = df[df["year"].isin(years)].copy()
    return df


def build_stage_map(naics_df: pd.DataFrame) -> dict[int, str]:
    """Use the most common stage per segment_id from NAICS rows."""
    stage_map: dict[int, str] = {}
    for seg_id, group in naics_df.groupby("segment_id"):
        stages = [s for s in group["stage"].dropna().astype(str).str.lower()]
        if stages:
            stage_map[seg_id] = Counter(stages).most_common(1)[0][0]
    return stage_map


def build_changes(df: pd.DataFrame, key_cols: list[str]) -> pd.DataFrame:
    """Return base (2024) employment and scenario deltas to 2030 for the given keys."""
    df = df.copy()
    base = (
        df[df["year"] == BASE_YEAR]
        .groupby(key_cols)["employment_auto"]
        .max()
        .rename("employment_auto_2024")
    )
    base = base.fillna(0.0)

    result = base.to_frame()
    for slug, label in SCENARIOS.items():
        target = (
            df[(df["year"] == TARGET_YEAR) & (df["forecast_source"] == slug)]
            .set_index(key_cols)["employment_auto"]
        )
        delta = target - base
        result[f"{label} change 2024-2030"] = result.index.map(delta)
    result.reset_index(inplace=True)
    return result


def format_name(text: str, indent: int) -> str:
    return ("  " * indent) + text


def append_summary(rows: list[dict], label: str, parts: list[dict]) -> None:
    """Append a summary row that sums the provided parts."""
    base = sum(p.get("employment_auto_2024", 0.0) for p in parts)
    # Collect change columns from the first part to keep ordering consistent.
    change_cols = [c for c in parts[0].keys() if "change 2024-2030" in c]
    deltas = {col: sum(p.get(col, 0.0) for p in parts) for col in change_cols}
    summary = {"Level": "Summary", "Name": label, "employment_auto_2024": base}
    summary.update(deltas)
    rows.append(summary)


def main() -> None:
    naics_ts = load_timeseries(NAICS_TS_PATH, YEARS)
    naics_ts = naics_ts.rename(columns={"projection_method": "forecast_source"})
    seg_ts = load_timeseries(SEG_TS_PATH, YEARS)
    stage_ts = load_timeseries(STAGE_TS_PATH, YEARS)

    stage_map = build_stage_map(naics_ts)

    stage_changes = build_changes(stage_ts, ["stage"])
    stage_changes["stage"] = stage_changes["stage"].astype(str).str.lower()
    stage_changes["stage_label"] = stage_changes["stage"].map(STAGE_LABELS).fillna(
        stage_changes["stage"].str.title()
    )

    seg_changes = build_changes(seg_ts, ["segment_id", "segment_name"])
    seg_changes["segment_id"] = seg_changes["segment_id"].astype(int)
    seg_changes["stage"] = seg_changes["segment_id"].map(stage_map)

    naics_changes = build_changes(naics_ts, ["naics_code", "naics_title", "segment_id"])
    naics_changes["segment_id"] = naics_changes["segment_id"].astype(int)
    naics_changes["stage"] = naics_changes["segment_id"].map(stage_map)

    change_cols = [
        "employment_auto_2024",
    ] + [f"{label} change 2024-2030" for label in SCENARIOS.values()]

    rows: list[dict] = []

    for stage_key in STAGE_ORDER:
        stage_row = stage_changes[stage_changes["stage"] == stage_key]
        if stage_row.empty:
            continue
        s = stage_row.iloc[0].to_dict()
        stage_entry = {"Level": "Stage", "Name": format_name(s["stage_label"], 0)}
        stage_entry.update({col: s[col] for col in change_cols})
        rows.append(stage_entry)

        seg_subset = seg_changes[seg_changes["stage"] == stage_key].sort_values("segment_id")
        stage_segments: list[dict] = []
        for _, seg in seg_subset.iterrows():
            seg_entry = {"Level": "Segment", "Name": format_name(seg["segment_name"], 1)}
            seg_entry.update({col: seg[col] for col in change_cols})
            rows.append(seg_entry)
            stage_segments.append(seg_entry)

            naics_subset = naics_changes[naics_changes["segment_id"] == seg["segment_id"]]
            naics_subset = naics_subset.sort_values("naics_code")
            for _, naics in naics_subset.iterrows():
                name = f"{naics['naics_code']} {naics['naics_title']}"
                naics_entry = {"Level": "NAICS", "Name": format_name(name, 2)}
                naics_entry.update({col: naics[col] for col in change_cols})
                rows.append(naics_entry)

        # Stage subtotal for sanity at the end of each stage block.
        if stage_segments:
            append_summary(rows, f"{s['stage_label']} total", stage_segments)

    # Additional rollups: Upstream + Core and Total using stage-level data.
    stage_totals = {
        row["stage_label"]: {col: row[col] for col in change_cols}
        for _, row in stage_changes.iterrows()
    }
    rows.append({"Level": "", "Name": ""})  # spacer
    upstream_core_parts = []
    for key in ("Upstream", "Core Automotive"):
        if key in stage_totals:
            part = {"employment_auto_2024": stage_totals[key]["employment_auto_2024"]}
            part.update({col: stage_totals[key][col] for col in change_cols if col != "employment_auto_2024"})
            upstream_core_parts.append(part)
    if upstream_core_parts:
        append_summary(rows, "Upstream + Core Automotive", upstream_core_parts)

    downstream_parts = []
    if "Downstream" in stage_totals:
        part = {"employment_auto_2024": stage_totals["Downstream"]["employment_auto_2024"]}
        part.update({col: stage_totals["Downstream"][col] for col in change_cols if col != "employment_auto_2024"})
        downstream_parts.append(part)
    if downstream_parts:
        append_summary(rows, "Downstream", downstream_parts)

    all_parts = []
    for label, metrics in stage_totals.items():
        part = {"employment_auto_2024": metrics["employment_auto_2024"]}
        part.update({col: metrics[col] for col in change_cols if col != "employment_auto_2024"})
        all_parts.append(part)
    if all_parts:
        append_summary(rows, "Total", all_parts)

    output_cols = ["Level", "Name"] + change_cols
    out_df = pd.DataFrame(rows)[output_cols]

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(OUT_PATH, engine="xlsxwriter") as writer:
        out_df.to_excel(writer, index=False, sheet_name="employment_change")
        ws = writer.sheets["employment_change"]
        num_fmt = writer.book.add_format({"num_format": "#,##0"})
        for idx, col in enumerate(output_cols):
            if col in change_cols:
                ws.set_column(idx, idx, 18, num_fmt)
            else:
                ws.set_column(idx, idx, 36)

    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
