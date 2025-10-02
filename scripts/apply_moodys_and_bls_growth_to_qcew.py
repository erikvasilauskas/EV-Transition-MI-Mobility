# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
import pandas as pd

# ---------------------
# Repo-relative paths
# ---------------------
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent

DATA_INTERIM   = REPO_ROOT / "data" / "interim"
DATA_PROCESSED = REPO_ROOT / "data" / "processed"
DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

# --- QCEW (levels) - Michigan
QCEW_SEG_MI = DATA_INTERIM / "mi_qcew_segment_employment_timeseries.csv"
QCEW_STG_MI = DATA_INTERIM / "mi_qcew_stage_employment_timeseries.csv"

# --- YoY (percent) sources ---
# Moody's (Michigan)
YOY_MOODY_SEG_MI = DATA_INTERIM / "moodys_michigan_segments_timeseries_yoy.csv"
YOY_MOODY_STG_MI = DATA_INTERIM / "moodys_michigan_stages_timeseries_yoy.csv"
# BLS (US)
YOY_BLS_SEG_US   = DATA_INTERIM / "bls_us_segments_timeseries_yoy.csv"
YOY_BLS_STG_US   = DATA_INTERIM / "bls_us_stages_timeseries_yoy.csv"

# --- Outputs: per-source extended levels (MI) ---
OUT_MOODY_SEG_MI = DATA_PROCESSED / "mi_qcew_segment_employment_timeseries_extended_moody.csv"
OUT_MOODY_STG_MI = DATA_PROCESSED / "mi_qcew_stage_employment_timeseries_extended_moody.csv"
OUT_BLS_SEG_MI   = DATA_PROCESSED / "mi_qcew_segment_employment_timeseries_extended_bls.csv"
OUT_BLS_STG_MI   = DATA_PROCESSED / "mi_qcew_stage_employment_timeseries_extended_bls.csv"

# --- Outputs: comparison (stacked) ---
OUT_COMPARE_SEG_MI = DATA_PROCESSED / "mi_qcew_segment_employment_timeseries_extended_compare.csv"
OUT_COMPARE_STG_MI = DATA_PROCESSED / "mi_qcew_stage_employment_timeseries_extended_compare.csv"

# --- (Placeholders for future US QCEW support) ---
# QCEW_SEG_US = DATA_INTERIM / "us_qcew_segment_employment_timeseries.csv"
# QCEW_STG_US = DATA_INTERIM / "us_qcew_stage_employment_timeseries.csv"
# OUT_MOODY_SEG_US = DATA_PROCESSED / "us_qcew_segment_employment_timeseries_extended_moody.csv"
# OUT_MOODY_STG_US = DATA_PROCESSED / "us_qcew_stage_employment_timeseries_extended_moody.csv"
# OUT_BLS_SEG_US   = DATA_PROCESSED / "us_qcew_segment_employment_timeseries_extended_bls.csv"
# OUT_BLS_STG_US   = DATA_PROCESSED / "us_qcew_stage_employment_timeseries_extended_bls.csv"
# OUT_COMPARE_SEG_US = DATA_PROCESSED / "us_qcew_segment_employment_timeseries_extended_compare.csv"
# OUT_COMPARE_STG_US = DATA_PROCESSED / "us_qcew_stage_employment_timeseries_extended_compare.csv"

def _require_exists(p: Path, label: str):
    if not p.exists():
        raise FileNotFoundError(f"Missing {label}: {p}")

def _coerce_int(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce").astype("Int64")

# -------------------------
# Cleaning / normalization
# -------------------------
def clean_qcew_segments(df: pd.DataFrame) -> pd.DataFrame:
    need = {"segment_id", "year", "employment_qcew"}
    missing = need - set(df.columns)
    if missing:
        raise ValueError(f"QCEW segments missing columns: {missing}")
    out = df.copy()
    # Standardize label/name field if present
    if "segment_label" in out.columns and "segment_name" not in out.columns:
        out = out.rename(columns={"segment_label": "segment_name"})
    out["segment_id"] = _coerce_int(out["segment_id"])
    out["year"] = _coerce_int(out["year"])
    out["employment_qcew"] = pd.to_numeric(out["employment_qcew"], errors="coerce")
    out = out.dropna(subset=["segment_id", "year"])
    out["segment_id"] = out["segment_id"].astype(int)
    out["year"] = out["year"].astype(int)
    # Keep optional segment_name if present
    keep_cols = ["segment_id", "segment_name", "year", "employment_qcew"]
    keep_cols = [c for c in keep_cols if c in out.columns]
    out = out[keep_cols].drop_duplicates(subset=["segment_id", "year"]).sort_values(["segment_id", "year"])
    return out.reset_index(drop=True)

def clean_qcew_stages(df: pd.DataFrame) -> pd.DataFrame:
    need = {"stage", "year", "employment_qcew"}
    missing = need - set(df.columns)
    if missing:
        raise ValueError(f"QCEW stages missing columns: {missing}")
    out = df.copy()
    out["stage"] = out["stage"].astype(str)
    out["year"] = _coerce_int(out["year"]).astype(int)
    out["employment_qcew"] = pd.to_numeric(out["employment_qcew"], errors="coerce")
    out = out.dropna(subset=["stage", "year"]).drop_duplicates(subset=["stage", "year"])
    out = out.sort_values(["stage", "year"]).reset_index(drop=True)
    return out

def clean_yoy_segments(df: pd.DataFrame) -> pd.DataFrame:
    need = {"segment_id", "year", "employment_yoy_pct"}
    missing = need - set(df.columns)
    if missing:
        raise ValueError(f"Segments YoY missing columns: {missing}")
    out = df.copy()
    out["segment_id"] = _coerce_int(out["segment_id"]).astype(int)
    out["year"] = _coerce_int(out["year"]).astype(int)
    out["employment_yoy_pct"] = pd.to_numeric(out["employment_yoy_pct"], errors="coerce")
    # Keep segment_name if present
    keep = ["segment_id", "year", "employment_yoy_pct"] + (["segment_name"] if "segment_name" in out.columns else [])
    out = out[keep].drop_duplicates(subset=["segment_id", "year"]).sort_values(["segment_id", "year"])
    return out.reset_index(drop=True)

def clean_yoy_stages(df: pd.DataFrame) -> pd.DataFrame:
    need = {"stage", "year", "employment_yoy_pct"}
    missing = need - set(df.columns)
    if missing:
        raise ValueError(f"Stages YoY missing columns: {missing}")
    out = df.copy()
    out["stage"] = out["stage"].astype(str)
    out["year"] = _coerce_int(out["year"]).astype(int)
    out["employment_yoy_pct"] = pd.to_numeric(out["employment_yoy_pct"], errors="coerce")
    out = out[["stage", "year", "employment_yoy_pct"]].drop_duplicates(subset=["stage", "year"])
    out = out.sort_values(["stage", "year"]).reset_index(drop=True)
    return out

# -------------------------
# Extension mechanics
# -------------------------
def extend_segments_with_yoy(qcew_seg: pd.DataFrame, yoy_seg: pd.DataFrame, source_name: str) -> pd.DataFrame:
    """
    Use YoY (percent) to extend QCEW segment levels forward.
    Output includes: segment_id, segment_name (if available), year, employment_qcew,
                     value_type (QCEW/Forecast), forecast_source (source_name),
                     applied_yoy_pct (percent).
    """
    pieces = []
    # Historical base
    hist = qcew_seg.copy()
    hist["value_type"] = "QCEW"
    hist["forecast_source"] = None
    hist["applied_yoy_pct"] = pd.NA
    pieces.append(hist)

    # Apply growth per segment
    by_seg = qcew_seg.groupby("segment_id", as_index=False)
    for seg_id, g in by_seg:
        last_year = int(g["year"].max())
        last_level = float(g.loc[g["year"].idxmax(), "employment_qcew"])
        seg_name = g["segment_name"].iloc[0] if "segment_name" in g.columns else None

        yoy = yoy_seg[yoy_seg["segment_id"] == seg_id]
        if yoy.empty:
            continue

        current = last_level
        f_rows = []
        for y in sorted(yoy["year"].unique()):
            if y <= last_year:
                continue
            rate = yoy.loc[yoy["year"] == y, "employment_yoy_pct"].iloc[0]
            if pd.isna(rate):
                continue
            growth = 1.0 + float(rate) / 100.0
            current = current * growth
            f_rows.append({
                "segment_id": seg_id,
                "segment_name": seg_name if seg_name is not None else (yoy["segment_name"].iloc[0] if "segment_name" in yoy.columns else None),
                "year": y,
                "employment_qcew": current,
                "value_type": "Forecast",
                "forecast_source": source_name,
                "applied_yoy_pct": rate,
            })
        if f_rows:
            pieces.append(pd.DataFrame(f_rows))

    out = pd.concat(pieces, ignore_index=True)
    # Drop overlap years; prefer QCEW over Forecast
    out["pref"] = out["value_type"].map({"QCEW": 0, "Forecast": 1})
    out = out.sort_values(["segment_id", "year", "pref"]).drop_duplicates(subset=["segment_id", "year"], keep="first").drop(columns=["pref"])
    return out.sort_values(["segment_id", "year"]).reset_index(drop=True)

def extend_stages_with_yoy(qcew_stg: pd.DataFrame, yoy_stg: pd.DataFrame, source_name: str) -> pd.DataFrame:
    pieces = []
    hist = qcew_stg.copy()
    hist["value_type"] = "QCEW"
    hist["forecast_source"] = None
    hist["applied_yoy_pct"] = pd.NA
    pieces.append(hist)

    by_stage = qcew_stg.groupby("stage", as_index=False)
    for stage, g in by_stage:
        last_year = int(g["year"].max())
        last_level = float(g.loc[g["year"].idxmax(), "employment_qcew"])

        yoy = yoy_stg[yoy_stg["stage"] == stage]
        if yoy.empty:
            continue

        current = last_level
        f_rows = []
        for y in sorted(yoy["year"].unique()):
            if y <= last_year:
                continue
            rate = yoy.loc[yoy["year"] == y, "employment_yoy_pct"].iloc[0]
            if pd.isna(rate):
                continue
            growth = 1.0 + float(rate) / 100.0
            current = current * growth
            f_rows.append({
                "stage": stage,
                "year": y,
                "employment_qcew": current,
                "value_type": "Forecast",
                "forecast_source": source_name,
                "applied_yoy_pct": rate,
            })
        if f_rows:
            pieces.append(pd.DataFrame(f_rows))

    out = pd.concat(pieces, ignore_index=True)
    out["pref"] = out["value_type"].map({"QCEW": 0, "Forecast": 1})
    out = out.sort_values(["stage", "year", "pref"]).drop_duplicates(subset=["stage", "year"], keep="first").drop(columns=["pref"])
    return out.sort_values(["stage", "year"]).reset_index(drop=True)

# -------------------------
# Main
# -------------------------
def main() -> None:
    # Ensure inputs
    _require_exists(QCEW_SEG_MI, "QCEW Michigan segments")
    _require_exists(QCEW_STG_MI, "QCEW Michigan stages")
    _require_exists(YOY_MOODY_SEG_MI, "Moody MI segments YoY")
    _require_exists(YOY_MOODY_STG_MI, "Moody MI stages YoY")
    _require_exists(YOY_BLS_SEG_US,   "BLS US segments YoY")
    _require_exists(YOY_BLS_STG_US,   "BLS US stages YoY")

    # Load & clean
    qcew_seg_mi = clean_qcew_segments(pd.read_csv(QCEW_SEG_MI))
    qcew_stg_mi = clean_qcew_stages(pd.read_csv(QCEW_STG_MI))

    moody_seg_mi = clean_yoy_segments(pd.read_csv(YOY_MOODY_SEG_MI))
    moody_stg_mi = clean_yoy_stages(pd.read_csv(YOY_MOODY_STG_MI))

    bls_seg_us   = clean_yoy_segments(pd.read_csv(YOY_BLS_SEG_US))
    bls_stg_us   = clean_yoy_stages(pd.read_csv(YOY_BLS_STG_US))

    # Extend with Moody's (MI)
    seg_mi_moody = extend_segments_with_yoy(qcew_seg_mi, moody_seg_mi, source_name="Moody")
    stg_mi_moody = extend_stages_with_yoy(qcew_stg_mi, moody_stg_mi, source_name="Moody")
    seg_mi_moody.to_csv(OUT_MOODY_SEG_MI, index=False)
    stg_mi_moody.to_csv(OUT_MOODY_STG_MI, index=False)

    # Extend with BLS (US)—applied to MI QCEW baseline as an alternative forecast assumption
    seg_mi_bls = extend_segments_with_yoy(qcew_seg_mi, bls_seg_us, source_name="BLS")
    stg_mi_bls = extend_stages_with_yoy(qcew_stg_mi, bls_stg_us, source_name="BLS")
    seg_mi_bls.to_csv(OUT_BLS_SEG_MI, index=False)
    stg_mi_bls.to_csv(OUT_BLS_STG_MI, index=False)

    print(f"Wrote: {OUT_MOODY_SEG_MI} (rows={len(seg_mi_moody)})")
    print(f"Wrote: {OUT_MOODY_STG_MI} (rows={len(stg_mi_moody)})")
    print(f"Wrote: {OUT_BLS_SEG_MI}   (rows={len(seg_mi_bls)})")
    print(f"Wrote: {OUT_BLS_STG_MI}   (rows={len(stg_mi_bls)})")

    # -------------------------
    # Build comparison (stacked)
    # -------------------------
    # Segments
    seg_common_cols = ["segment_id", "segment_name", "year", "employment_qcew", "value_type", "forecast_source", "applied_yoy_pct"]
    seg_cmp = pd.concat([
        seg_mi_moody[seg_common_cols],
        seg_mi_bls[seg_common_cols]
    ], ignore_index=True).sort_values(["segment_id", "year", "forecast_source", "value_type"])
    # If there are duplicate (QCEW) rows across stacks, keep first
    seg_cmp = seg_cmp.drop_duplicates(subset=["segment_id", "year", "value_type", "forecast_source"], keep="first")
    seg_cmp.to_csv(OUT_COMPARE_SEG_MI, index=False)

    # Stages
    stg_common_cols = ["stage", "year", "employment_qcew", "value_type", "forecast_source", "applied_yoy_pct"]
    stg_cmp = pd.concat([
        stg_mi_moody[stg_common_cols],
        stg_mi_bls[stg_common_cols]
    ], ignore_index=True).sort_values(["stage", "year", "forecast_source", "value_type"])
    stg_cmp = stg_cmp.drop_duplicates(subset=["stage", "year", "value_type", "forecast_source"], keep="first")
    stg_cmp.to_csv(OUT_COMPARE_STG_MI, index=False)

    print(f"Wrote: {OUT_COMPARE_SEG_MI} (rows={len(seg_cmp)})")
    print(f"Wrote: {OUT_COMPARE_STG_MI} (rows={len(stg_cmp)})")

    # --- Future US support (uncomment and mirror the MI flow once you add US QCEW) ---
    # _require_exists(QCEW_SEG_US, "QCEW US segments")
    # _require_exists(QCEW_STG_US, "QCEW US stages")
    # qcew_seg_us = clean_qcew_segments(pd.read_csv(QCEW_SEG_US))
    # qcew_stg_us = clean_qcew_stages(pd.read_csv(QCEW_STG_US))
    # seg_us_moody = extend_segments_with_yoy(qcew_seg_us, moody_seg_us, source_name="Moody")
    # stg_us_moody = extend_stages_with_yoy(qcew_stg_us, moody_stg_us, source_name="Moody")
    # seg_us_bls   = extend_segments_with_yoy(qcew_seg_us, bls_seg_us,   source_name="BLS")
    # stg_us_bls   = extend_stages_with_yoy(qcew_stg_us, bls_stg_us,     source_name="BLS")
    # seg_us_cmp = pd.concat([seg_us_moody[seg_common_cols], seg_us_bls[seg_common_cols]], ignore_index=True)
    # stg_us_cmp = pd.concat([stg_us_moody[stg_common_cols], stg_us_bls[stg_common_cols]], ignore_index=True)
    # seg_us_moody.to_csv(OUT_MOODY_SEG_US, index=False)
    # stg_us_moody.to_csv(OUT_MOODY_STG_US, index=False)
    # seg_us_bls.to_csv(OUT_BLS_SEG_US, index=False)
    # stg_us_bls.to_csv(OUT_BLS_STG_US, index=False)
    # seg_us_cmp.to_csv(OUT_COMPARE_SEG_US, index=False)
    # stg_us_cmp.to_csv(OUT_COMPARE_STG_US, index=False)

if __name__ == "__main__":
    main()
