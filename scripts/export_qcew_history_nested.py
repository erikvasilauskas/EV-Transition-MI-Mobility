# -*- coding: utf-8 -*-
"""Build nested QCEW employment table (2001, 2009, 2019, 2024) for stage/segment/NAICS."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data" / "processed" / "sam_auto_dashboard_2024_refresh"
NAICS_TS_PATH = DATA_DIR / "sam_employment_naics_timeseries.csv"
SEG_TS_PATH = DATA_DIR / "sam_employment_segment_timeseries.csv"
STAGE_TS_PATH = DATA_DIR / "sam_employment_stage_timeseries.csv"
OUT_PATH = DATA_DIR / "custom_table_output" / "qcew_stage_segment_naics_2001_2009_2019_2024.xlsx"

YEARS = (2001, 2009, 2019, 2024)

SCENARIO = "bls_us"
STAGE_ORDER = ["upstream", "core automotive", "downstream"]
STAGE_LABELS = {
    "upstream": "Upstream",
    "core automotive": "Core Automotive",
    "oem": "Core Automotive",
    "upstream + core automotive": "Upstream + Core Automotive",
    "downstream": "Downstream",
}


def load_timeseries(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_csv(path)
    df = df[df["year"].isin(YEARS)].copy()
    return df


def build_stage_map(naics_df: pd.DataFrame) -> dict[int, str]:
    """Use the most common stage per segment_id from NAICS rows."""
    stage_map: dict[int, str] = {}
    for seg_id, group in naics_df.groupby("segment_id"):
        stages = [s for s in group["stage"].dropna().astype(str).str.lower()]
        if stages:
            stage_map[seg_id] = Counter(stages).most_common(1)[0][0]
    return stage_map


def pivot_values(df: pd.DataFrame, key_cols: list[str], value_col: str) -> pd.DataFrame:
    """Aggregate employment and pivot wide by year."""
    grouped = df.groupby(key_cols + ["year"], as_index=False)[value_col].sum()
    wide = grouped.pivot(index=key_cols, columns="year", values=value_col)
    wide = wide.reindex(columns=YEARS)
    wide.reset_index(inplace=True)
    return wide


def format_name(text: str, indent: int) -> str:
    return ("  " * indent) + text


def build_nested_rows(stage_wide: pd.DataFrame, seg_wide: pd.DataFrame, naics_wide: pd.DataFrame, rename_years: dict[int, str]) -> list[dict]:
    rows: list[dict] = []
    stage_entries: list[dict] = []

    for stage_key in STAGE_ORDER:
        stage_row = stage_wide[stage_wide["stage"] == stage_key]
        if stage_row.empty:
            continue
        s = stage_row.iloc[0]
        stage_entry = {"Level": "Stage", "Name": format_name(s["stage_label"], 0)}
        stage_entry.update({rename_years[y]: s.get(y, 0.0) for y in YEARS})
        rows.append(stage_entry)
        stage_entries.append(stage_entry)

        seg_subset = seg_wide[seg_wide["stage"] == stage_key].sort_values("segment_id")
        for _, seg in seg_subset.iterrows():
            seg_entry = {"Level": "Segment", "Name": format_name(seg["segment_name"], 1)}
            seg_entry.update({rename_years[y]: seg.get(y, 0.0) for y in YEARS})
            rows.append(seg_entry)

            naics_subset = naics_wide[naics_wide["segment_id"] == seg["segment_id"]]
            naics_subset = naics_subset.sort_values("naics_code")
            for _, naics in naics_subset.iterrows():
                name = f"{naics['naics_code']} {naics['naics_title']}"
                naics_entry = {"Level": "NAICS", "Name": format_name(name, 2)}
                naics_entry.update({rename_years[y]: naics.get(y, 0.0) for y in YEARS})
                rows.append(naics_entry)

    # Total across all stages.
    if stage_entries:
        total_row = {"Level": "Summary", "Name": "Total, all segments"}
        for y in YEARS:
            col = rename_years[y]
            total_row[col] = sum(r.get(col, 0.0) for r in stage_entries)
        rows.append(total_row)
    return rows


def main() -> None:
    naics_ts = load_timeseries(NAICS_TS_PATH)
    # NAICS file uses projection_method instead of forecast_source; keep all rows since QCEW is common.
    naics_ts = naics_ts.rename(columns={"projection_method": "forecast_source"})
    naics_ts = naics_ts[naics_ts["forecast_source"] == SCENARIO]
    seg_ts = load_timeseries(SEG_TS_PATH)
    seg_ts = seg_ts[seg_ts["forecast_source"] == SCENARIO]
    stage_ts = load_timeseries(STAGE_TS_PATH)
    stage_ts = stage_ts[stage_ts["forecast_source"] == SCENARIO]

    stage_map = build_stage_map(naics_ts)

    stage_wide_raw = pivot_values(stage_ts, ["stage"], "employment_raw")
    stage_wide_raw["stage"] = stage_wide_raw["stage"].astype(str).str.lower()
    stage_wide_raw["stage_label"] = stage_wide_raw["stage"].map(STAGE_LABELS).fillna(
        stage_wide_raw["stage"].str.title()
    )
    seg_wide_raw = pivot_values(seg_ts, ["segment_id", "segment_name"], "employment_raw")
    seg_wide_raw["segment_id"] = seg_wide_raw["segment_id"].astype(int)
    seg_wide_raw["stage"] = seg_wide_raw["segment_id"].map(stage_map)
    naics_wide_raw = pivot_values(naics_ts, ["naics_code", "naics_title", "segment_id"], "employment_raw")
    naics_wide_raw["segment_id"] = naics_wide_raw["segment_id"].astype(int)
    naics_wide_raw["stage"] = naics_wide_raw["segment_id"].map(stage_map)

    stage_wide_auto = pivot_values(stage_ts, ["stage"], "employment_auto")
    stage_wide_auto["stage"] = stage_wide_auto["stage"].astype(str).str.lower()
    stage_wide_auto["stage_label"] = stage_wide_auto["stage"].map(STAGE_LABELS).fillna(
        stage_wide_auto["stage"].str.title()
    )
    seg_wide_auto = pivot_values(seg_ts, ["segment_id", "segment_name"], "employment_auto")
    seg_wide_auto["segment_id"] = seg_wide_auto["segment_id"].astype(int)
    seg_wide_auto["stage"] = seg_wide_auto["segment_id"].map(stage_map)
    naics_wide_auto = pivot_values(naics_ts, ["naics_code", "naics_title", "segment_id"], "employment_auto")
    naics_wide_auto["segment_id"] = naics_wide_auto["segment_id"].astype(int)
    naics_wide_auto["stage"] = naics_wide_auto["segment_id"].map(stage_map)

    raw_cols = ["Employment QCEW " + str(y) for y in YEARS]
    raw_rename = {y: f"Employment QCEW {y}" for y in YEARS}
    auto_cols = ["Employment Auto " + str(y) for y in YEARS]
    auto_rename = {y: f"Employment Auto {y}" for y in YEARS}

    raw_rows = build_nested_rows(stage_wide_raw, seg_wide_raw, naics_wide_raw, raw_rename)
    auto_rows = build_nested_rows(stage_wide_auto, seg_wide_auto, naics_wide_auto, auto_rename)

    raw_df = pd.DataFrame(raw_rows)[["Level", "Name"] + raw_cols]
    auto_df = pd.DataFrame(auto_rows)[["Level", "Name"] + auto_cols]

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    def write_file(path: Path) -> None:
        with pd.ExcelWriter(path, engine="xlsxwriter") as writer:
            raw_df.to_excel(writer, index=False, sheet_name="qcew_history")
            auto_df.to_excel(writer, index=False, sheet_name="auto_history")
            num_fmt = writer.book.add_format({"num_format": "#,##0"})
            for sheet, cols in [("qcew_history", raw_cols), ("auto_history", auto_cols)]:
                ws = writer.sheets[sheet]
                for idx, col in enumerate(["Level", "Name"] + cols):
                    if col in cols:
                        ws.set_column(idx, idx, 18, num_fmt)
                    else:
                        ws.set_column(idx, idx, 42)

    try:
        write_file(OUT_PATH)
        print(f"Wrote {OUT_PATH}")
    except PermissionError:
        alt_path = OUT_PATH.with_name(f"{OUT_PATH.stem}_bls_us.xlsx")
        write_file(alt_path)
        print(f"Primary path locked; wrote fallback file {alt_path}")


if __name__ == "__main__":
    main()
