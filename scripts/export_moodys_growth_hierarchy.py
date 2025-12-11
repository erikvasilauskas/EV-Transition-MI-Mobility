"""Build nested stage/segment/NAICS tables for Moody's MI scenario (2024 vs 2030).

Outputs two sheets:
  - auto: automotive-adjusted employment
  - raw: raw employment

Hierarchy:
  Stage (Upstream/OEM/Downstream)
    Segment (1-10)
      NAICS (code + title)
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data" / "processed" / "sam_auto_dashboard_2024_refresh"
NAICS_TS_PATH = DATA_DIR / "sam_employment_naics_timeseries.csv"
SEG_TS_PATH = DATA_DIR / "sam_employment_segment_timeseries.csv"
STAGE_TS_PATH = DATA_DIR / "sam_employment_stage_timeseries.csv"
OUT_DIR = DATA_DIR / "custom_table_output"
OUT_PATH = OUT_DIR / "moodys_mi_stage_segment_naics_2024_2030.xlsx"

SCENARIO = "moodys_mi"
YEARS = (2024, 2030)
STAGE_ORDER = ["upstream", "core automotive", "downstream"]
STAGE_LABELS = {
    "upstream": "Upstream",
    "core automotive": "Core Automotive",
    "oem": "Core Automotive",
    "upstream + core automotive": "Upstream + Core Automotive",
    "downstream": "Downstream",
}


def _pivot_levels(df: pd.DataFrame, value_col_auto: str, value_col_raw: str, label_cols: list[str]) -> pd.DataFrame:
    """Pivot to wide for 2024/2030 auto/raw plus change/pct."""
    wide_auto = df.pivot_table(index=label_cols, columns="year", values=value_col_auto)
    wide_raw = df.pivot_table(index=label_cols, columns="year", values=value_col_raw)
    out = wide_auto.reindex(columns=YEARS).rename(
        columns={YEARS[0]: "auto_2024", YEARS[1]: "auto_2030"}
    )
    out["raw_2024"] = wide_raw.get(YEARS[0])
    out["raw_2030"] = wide_raw.get(YEARS[1])
    out = out.reset_index()
    return out


def _add_change_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["auto_change"] = df["auto_2030"] - df["auto_2024"]
    df["auto_pct_change"] = np.where(df["auto_2024"] != 0, df["auto_change"] / df["auto_2024"], np.nan)
    df["raw_change"] = df["raw_2030"] - df["raw_2024"]
    df["raw_pct_change"] = np.where(df["raw_2024"] != 0, df["raw_change"] / df["raw_2024"], np.nan)
    return df


def main() -> None:
    naics_ts = pd.read_csv(NAICS_TS_PATH)
    seg_ts = pd.read_csv(SEG_TS_PATH)
    stage_ts = pd.read_csv(STAGE_TS_PATH)

    naics_ts = naics_ts[naics_ts["projection_method"] == SCENARIO].copy()
    seg_ts = seg_ts[seg_ts["forecast_source"] == SCENARIO].copy()
    stage_ts = stage_ts[stage_ts["forecast_source"] == SCENARIO].copy()

    naics_ts = naics_ts[naics_ts["year"].isin(YEARS)]
    seg_ts = seg_ts[seg_ts["year"].isin(YEARS)]
    stage_ts = stage_ts[stage_ts["year"].isin(YEARS)]

    # Map segment_id -> stage using NAICS metadata (most common stage per segment)
    stage_map = {}
    for seg_id, group in naics_ts.groupby("segment_id"):
        stages = [s for s in group["stage"].dropna().astype(str).str.lower()]
        if stages:
            stage_map[seg_id] = Counter(stages).most_common(1)[0][0]

    # Stage-level wide table
    stage_wide = _pivot_levels(stage_ts, "employment_auto", "employment_raw", ["stage"])
    stage_wide["stage"] = stage_wide["stage"].astype(str).str.lower()
    stage_wide["stage_label"] = stage_wide["stage"].map(STAGE_LABELS).fillna(stage_wide["stage"].str.title())
    stage_wide = _add_change_cols(stage_wide)

    # Segment-level wide table
    seg_wide = _pivot_levels(seg_ts, "employment_auto", "employment_raw", ["segment_id", "segment_name"])
    seg_wide["segment_id"] = seg_wide["segment_id"].astype(int)
    seg_wide["stage"] = seg_wide["segment_id"].map(stage_map)
    seg_wide = _add_change_cols(seg_wide)

    # NAICS-level wide table
    naics_wide = _pivot_levels(
        naics_ts,
        "employment_auto",
        "employment_raw",
        ["naics_code", "naics_title", "segment_id"],
    )
    naics_wide["segment_id"] = naics_wide["segment_id"].astype(int)
    naics_wide["stage"] = naics_wide["segment_id"].map(stage_map)
    naics_wide = _add_change_cols(naics_wide)

    # Build nested rows
    def fmt_name(label: str, level: int) -> str:
        return ("  " * level) + label

    rows_auto = []
    rows_raw = []

    def append_rows(stage_key: str, stage_label: str):
        stage_row = stage_wide[stage_wide["stage"] == stage_key]
        if stage_row.empty:
            return
        sr = stage_row.iloc[0]
        rows_auto.append(
            {
                "name": fmt_name(stage_label, 0),
                "employment_2024": sr["auto_2024"],
                "employment_2030": sr["auto_2030"],
                "employment_change": sr["auto_change"],
                "pct_change": sr["auto_pct_change"],
            }
        )
        rows_raw.append(
            {
                "name": fmt_name(stage_label, 0),
                "employment_2024": sr["raw_2024"],
                "employment_2030": sr["raw_2030"],
                "employment_change": sr["raw_change"],
                "pct_change": sr["raw_pct_change"],
            }
        )
        seg_subset = seg_wide[seg_wide["stage"] == stage_key].sort_values("segment_id")
        for _, seg in seg_subset.iterrows():
            seg_label = str(seg["segment_name"])
            rows_auto.append(
                {
                    "name": fmt_name(seg_label, 1),
                    "employment_2024": seg["auto_2024"],
                    "employment_2030": seg["auto_2030"],
                    "employment_change": seg["auto_change"],
                    "pct_change": seg["auto_pct_change"],
                }
            )
            rows_raw.append(
                {
                    "name": fmt_name(seg_label, 1),
                    "employment_2024": seg["raw_2024"],
                    "employment_2030": seg["raw_2030"],
                    "employment_change": seg["raw_change"],
                    "pct_change": seg["raw_pct_change"],
                }
            )
            naics_subset = naics_wide[naics_wide["segment_id"] == seg["segment_id"]].sort_values("naics_code")
            for _, na in naics_subset.iterrows():
                na_label = f"NAICS {na['naics_code']} - {na['naics_title']}"
                rows_auto.append(
                    {
                        "name": fmt_name(na_label, 2),
                        "employment_2024": na["auto_2024"],
                        "employment_2030": na["auto_2030"],
                        "employment_change": na["auto_change"],
                        "pct_change": na["auto_pct_change"],
                    }
                )
                rows_raw.append(
                    {
                        "name": fmt_name(na_label, 2),
                        "employment_2024": na["raw_2024"],
                        "employment_2030": na["raw_2030"],
                        "employment_change": na["raw_change"],
                        "pct_change": na["raw_pct_change"],
                    }
                )

    for key in STAGE_ORDER:
        label = STAGE_LABELS.get(key, key.title())
        append_rows(key, label)

    auto_df = pd.DataFrame(rows_auto)
    raw_df = pd.DataFrame(rows_raw)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(OUT_PATH, engine="xlsxwriter") as writer:
        auto_df.to_excel(writer, sheet_name="auto", index=False)
        raw_df.to_excel(writer, sheet_name="raw", index=False)
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
