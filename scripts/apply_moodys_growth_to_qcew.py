# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
import os
import pandas as pd

# ---------------------
# Repo-relative paths
# ---------------------
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent

DATA_INTERIM = REPO_ROOT / "data" / "interim"
DATA_PROCESSED = REPO_ROOT / "data" / "processed"
DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

# --- Inputs (MI only, per your request) ---
QCEW_SEG_MI = DATA_INTERIM / "mi_qcew_segment_employment_timeseries.csv"
QCEW_STG_MI = DATA_INTERIM / "mi_qcew_stage_employment_timeseries.csv"

YOY_SEG_MI  = DATA_INTERIM / "moodys_michigan_segments_timeseries_yoy.csv"
YOY_STG_MI  = DATA_INTERIM / "moodys_michigan_stages_timeseries_yoy.csv"

# --- (Placeholders for future US support) ---
# QCEW_SEG_US = DATA_INTERIM / "us_qcew_segment_employment_timeseries.csv"
# QCEW_STG_US = DATA_INTERIM / "us_qcew_stage_employment_timeseries.csv"
# YOY_SEG_US  = DATA_INTERIM / "moodys_us_segments_timeseries_yoy.csv"
# YOY_STG_US  = DATA_INTERIM / "moodys_us_stages_timeseries_yoy.csv"

# --- Outputs ---
OUT_SEG_MI = DATA_PROCESSED / "mi_qcew_segment_employment_timeseries_extended.csv"
OUT_STG_MI = DATA_PROCESSED / "mi_qcew_stage_employment_timeseries_extended.csv"

# --- Columns we expect ---
# QCEW segments: ["segment_id", "segment_label", "year", "employment_qcew"]
# QCEW stages:   ["stage", "year", "employment_qcew"]
# Moody's YoY segments: ["segment_id","segment_name","year","employment_yoy_pct",...]
# Moody's YoY stages:   ["stage","year","employment_yoy_pct",...]

def _require_exists(p: Path, label: str):
    if not p.exists():
        raise FileNotFoundError(f"Missing {label}: {p}")

def _coerce_int(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").astype("Int64")

def _clean_qcew_segment(df: pd.DataFrame) -> pd.DataFrame:
    need = {"segment_id", "segment_label", "year", "employment_qcew"}
    missing = need - set(df.columns)
    if missing:
        raise ValueError(f"QCEW segment file missing columns: {missing}")
    out = df.copy()
    out["segment_id"] = _coerce_int(out["segment_id"])
    out["year"] = _coerce_int(out["year"])
    out["employment_qcew"] = pd.to_numeric(out["employment_qcew"], errors="coerce")
    out = out.dropna(subset=["segment_id", "year"])
    out["segment_id"] = out["segment_id"].astype(int)
    out["year"] = out["year"].astype(int)
    return out.sort_values(["segment_id", "year"]).reset_index(drop=True)

def _clean_qcew_stage(df: pd.DataFrame) -> pd.DataFrame:
    need = {"stage", "year", "employment_qcew"}
    missing = need - set(df.columns)
    if missing:
        raise ValueError(f"QCEW stage file missing columns: {missing}")
    out = df.copy()
    out["stage"] = out["stage"].astype(str)
    out["year"] = _coerce_int(out["year"]).astype(int)
    out["employment_qcew"] = pd.to_numeric(out["employment_qcew"], errors="coerce")
    out = out.dropna(subset=["stage", "year"])
    return out.sort_values(["stage", "year"]).reset_index(drop=True)

def _clean_yoy_segment(df: pd.DataFrame) -> pd.DataFrame:
    need = {"segment_id", "year", "employment_yoy_pct"}
    missing = need - set(df.columns)
    if missing:
        raise ValueError(f"Moody's segment YoY file missing columns: {missing}")
    out = df.copy()
    out["segment_id"] = _coerce_int(out["segment_id"]).astype(int)
    out["year"] = _coerce_int(out["year"]).astype(int)
    out["employment_yoy_pct"] = pd.to_numeric(out["employment_yoy_pct"], errors="coerce")
    # keep segment_name if present; ensure dedupe per key
    out = out.drop_duplicates(subset=["segment_id", "year"]).reset_index(drop=True)
    return out.sort_values(["segment_id", "year"]).reset_index(drop=True)

def _clean_yoy_stage(df: pd.DataFrame) -> pd.DataFrame:
    need = {"stage", "year", "employment_yoy_pct"}
    missing = need - set(df.columns)
    if missing:
        raise ValueError(f"Moody's stage YoY file missing columns: {missing}")
    out = df.copy()
    out["stage"] = out["stage"].astype(str)
    out["year"] = _coerce_int(out["year"]).astype(int)
    out["employment_yoy_pct"] = pd.to_numeric(out["employment_yoy_pct"], errors="coerce")
    out = out.drop_duplicates(subset=["stage", "year"]).reset_index(drop=True)
    return out.sort_values(["stage", "year"]).reset_index(drop=True)

def _extend_with_yoy_segments(qcew: pd.DataFrame, yoy: pd.DataFrame) -> pd.DataFrame:
    """
    For each segment_id, take the last QCEW level and apply Moody's employment_yoy_pct
    for subsequent years to generate forecast levels.
    Adds value_type = {"QCEW","MoodyForecast"} and preserves segment_label.
    """
    pieces = []

    # historical portion flagged
    hist = qcew.copy()
    hist["value_type"] = "QCEW"
    hist["moody_employment_yoy_pct"] = pd.NA  # optional helper column
    pieces.append(hist)

    # per-segment forecast
    by_seg = qcew.groupby("segment_id")
    for seg_id, g in by_seg:
        last_year = int(g["year"].max())
        last_level = float(g.loc[g["year"].idxmax(), "employment_qcew"])
        seg_label = g["segment_label"].iloc[0] if "segment_label" in g.columns else None

        yoy_seg = yoy[yoy["segment_id"] == seg_id].copy()
        if yoy_seg.empty:
            continue

        # Iterate forward from last_year+1 to max YoY year
        forecast_rows = []
        current = last_level
        for y in sorted(yoy_seg["year"].unique()):
            if y <= last_year:
                continue
            rate = yoy_seg.loc[yoy_seg["year"] == y, "employment_yoy_pct"].iloc[0]
            if pd.isna(rate):
                # skip missing growth years
                continue
            growth = 1.0 + float(rate) / 100.0
            current = current * growth
            forecast_rows.append({
                "segment_id": seg_id,
                "segment_label": seg_label if seg_label is not None else
                                 yoy_seg.get("segment_name", pd.Series([None])).iloc[0],
                "year": y,
                "employment_qcew": current,
                "value_type": "MoodyForecast",
                "moody_employment_yoy_pct": rate,
            })

        if forecast_rows:
            pieces.append(pd.DataFrame(forecast_rows))

    out = pd.concat(pieces, ignore_index=True)
    # Drop any accidental duplicates, prefer QCEW over forecast if overlap
    out = out.sort_values(["segment_id", "year", "value_type"])  # "MoodyForecast" > "QCEW" lexically, but we handle next:
    out = out.drop_duplicates(subset=["segment_id", "year"], keep="first")
    return out.sort_values(["segment_id", "year"]).reset_index(drop=True)

def _extend_with_yoy_stages(qcew: pd.DataFrame, yoy: pd.DataFrame) -> pd.DataFrame:
    """
    Same approach as segments, but keyed by stage.
    """
    pieces = []
    hist = qcew.copy()
    hist["value_type"] = "QCEW"
    hist["moody_employment_yoy_pct"] = pd.NA
    pieces.append(hist)

    by_stage = qcew.groupby("stage")
    for stage, g in by_stage:
        last_year = int(g["year"].max())
        last_level = float(g.loc[g["year"].idxmax(), "employment_qcew"])

        yoy_st = yoy[yoy["stage"] == stage].copy()
        if yoy_st.empty:
            continue

        forecast_rows = []
        current = last_level
        for y in sorted(yoy_st["year"].unique()):
            if y <= last_year:
                continue
            rate = yoy_st.loc[yoy_st["year"] == y, "employment_yoy_pct"].iloc[0]
            if pd.isna(rate):
                continue
            growth = 1.0 + float(rate) / 100.0
            current = current * growth
            forecast_rows.append({
                "stage": stage,
                "year": y,
                "employment_qcew": current,
                "value_type": "MoodyForecast",
                "moody_employment_yoy_pct": rate,
            })

        if forecast_rows:
            pieces.append(pd.DataFrame(forecast_rows))

    out = pd.concat(pieces, ignore_index=True)
    out = out.sort_values(["stage", "year", "value_type"])
    out = out.drop_duplicates(subset=["stage", "year"], keep="first")
    return out.sort_values(["stage", "year"]).reset_index(drop=True)

def main() -> None:
    # --- Ensure inputs exist
    _require_exists(QCEW_SEG_MI, "QCEW Michigan segments")
    _require_exists(QCEW_STG_MI, "QCEW Michigan stages")
    _require_exists(YOY_SEG_MI,  "Moody's Michigan segments YoY")
    _require_exists(YOY_STG_MI,  "Moody's Michigan stages YoY")

    # --- Load & clean
    qcew_seg_mi = _clean_qcew_segment(pd.read_csv(QCEW_SEG_MI))
    qcew_stg_mi = _clean_qcew_stage(pd.read_csv(QCEW_STG_MI))

    yoy_seg_mi  = _clean_yoy_segment(pd.read_csv(YOY_SEG_MI))
    yoy_stg_mi  = _clean_yoy_stage(pd.read_csv(YOY_STG_MI))

    # --- Extend with Moody's YoY
    seg_mi_ext = _extend_with_yoy_segments(qcew_seg_mi, yoy_seg_mi)
    stg_mi_ext = _extend_with_yoy_stages(qcew_stg_mi, yoy_stg_mi)

    # --- Save
    seg_mi_ext.to_csv(OUT_SEG_MI, index=False)
    stg_mi_ext.to_csv(OUT_STG_MI, index=False)

    print(f"Wrote: {OUT_SEG_MI}  (rows={len(seg_mi_ext)}, years {seg_mi_ext['year'].min()}–{seg_mi_ext['year'].max()})")
    print(f"Wrote: {OUT_STG_MI}  (rows={len(stg_mi_ext)}, years {stg_mi_ext['year'].min()}–{stg_mi_ext['year'].max()})")

    # --- Future US support (uncomment when you have US QCEW levels)
    # _require_exists(QCEW_SEG_US, "QCEW US segments")
    # _require_exists(QCEW_STG_US, "QCEW US stages")
    # _require_exists(YOY_SEG_US,  "Moody's US segments YoY")
    # _require_exists(YOY_STG_US,  "Moody's US stages YoY")
    #
    # qcew_seg_us = _clean_qcew_segment(pd.read_csv(QCEW_SEG_US))
    # qcew_stg_us = _clean_qcew_stage(pd.read_csv(QCEW_STG_US))
    # yoy_seg_us  = _clean_yoy_segment(pd.read_csv(YOY_SEG_US))
    # yoy_stg_us  = _clean_yoy_stage(pd.read_csv(YOY_STG_US))
    #
    # seg_us_ext = _extend_with_yoy_segments(qcew_seg_us, yoy_seg_us)
    # stg_us_ext = _extend_with_yoy_stages(qcew_stg_us, yoy_stg_us)
    #
    # OUT_SEG_US = DATA_PROCESSED / "us_qcew_segment_employment_timeseries_extended.csv"
    # OUT_STG_US = DATA_PROCESSED / "us_qcew_stage_employment_timeseries_extended.csv"
    # seg_us_ext.to_csv(OUT_SEG_US, index=False)
    # stg_us_ext.to_csv(OUT_STG_US, index=False)
    # print(f"Wrote: {OUT_SEG_US}")
    # print(f"Wrote: {OUT_STG_US}")

if __name__ == "__main__":
    main()
