# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
import math
import pandas as pd

# ---------------------
# Repo-relative paths
# ---------------------
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent

INPUT_BLS = REPO_ROOT / "data" / "processed" / "us_staffing_segments_summary.csv"
LOOKUP_SEGMENT = REPO_ROOT / "data" / "lookups" / "segment_assignments.csv"  # optional, used if 'stage' missing
OUT_DIR = REPO_ROOT / "data" / "interim"
OUT_DIR.mkdir(parents=True, exist_ok=True)

OUT_SEG = OUT_DIR / "bls_us_segments_timeseries_yoy.csv"
OUT_STG = OUT_DIR / "bls_us_stages_timeseries_yoy.csv"

OCCUPATION_CODE_TARGET = "00-0000"  # Total, all occupations
Y_START = 2024
Y_END = 2034
YEARS_YOY = list(range(Y_START + 1, Y_END + 1))  # 2025..2034 inclusive
# Column name candidates in the source file (be flexible)
OCC_CODE_COLS = ["Occupation Code", "occupation_code", "occ_code", "OCC_CODE"]
OCC_TITLE_COLS = ["Occupation Title", "occupation_title", "occ_title", "OCC_TITLE"]
SEG_ID_COLS = ["segment_id", "Segment ID", "segmentId"]
SEG_NAME_COLS = ["segment_name", "segment_label", "Segment", "Segment Name"]
STAGE_COLS = ["stage", "Stage"]
EMP24_COLS = ["2024 Employment", "Employment 2024", "Employment_2024", "emp_2024", "Employment (2024)"]
EMP34_COLS = ["Projected 2034 Employment", "2034 Employment", "Employment 2034", "Employment_2034", "emp_2034", "Projected Employment 2034"]

def _require_exists(p: Path, label: str):
    if not p.exists():
        raise FileNotFoundError(f"Missing {label}: {p}")

def _find_first_col(df: pd.DataFrame, candidates: list[str], required=True) -> str | None:
    for c in candidates:
        if c in df.columns:
            return c
    if required:
        raise KeyError(f"Could not find any of columns {candidates} in input.")
    return None

def _coerce_num(s):
    return pd.to_numeric(s, errors="coerce")

def _load_lookup_stage() -> pd.DataFrame | None:
    """Load segment_id -> stage mapping if available."""
    if not LOOKUP_SEGMENT.exists():
        return None
    lk = pd.read_csv(LOOKUP_SEGMENT)
    if "segment_id" not in lk.columns or "stage" not in lk.columns:
        return None
    # one row per segment_id -> stage
    lk = lk[["segment_id", "stage"]].dropna().drop_duplicates(subset=["segment_id"])
    try:
        lk["segment_id"] = pd.to_numeric(lk["segment_id"], errors="coerce").astype("Int64")
    except Exception:
        pass
    return lk

def _ensure_stage(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure a 'stage' column exists; if not, try to map via lookup."""
    if "stage" in df.columns:
        return df
    # try lookup
    lk = _load_lookup_stage()
    if lk is None:
        raise KeyError("Stage column missing in BLS file and no usable mapping in segment_assignments.csv.")
    out = df.merge(lk, on="segment_id", how="left", validate="many_to_one")
    if out["stage"].isna().any():
        missing = sorted(out.loc[out["stage"].isna(), "segment_id"].dropna().unique().tolist())
        raise ValueError(f"Missing stage mapping for segment_id(s): {missing}")
    return out

def _read_bls_source() -> pd.DataFrame:
    _require_exists(INPUT_BLS, "US staffing summary (BLS)")
    df = pd.read_csv(INPUT_BLS)

    # Resolve column names
    occ_col = _find_first_col(df, OCC_CODE_COLS, required=True)
    seg_id_col = _find_first_col(df, SEG_ID_COLS, required=True)
    seg_name_col = _find_first_col(df, SEG_NAME_COLS, required=True)
    emp24_col = _find_first_col(df, EMP24_COLS, required=True)
    emp34_col = _find_first_col(df, EMP34_COLS, required=True)
    stage_col = _find_first_col(df, STAGE_COLS, required=False)  # may be None

    # Filter to Total, all occupations
    df = df.loc[df[occ_col].astype(str).str.strip() == OCCUPATION_CODE_TARGET].copy()

    # Keep relevant columns, rename to canonical names
    keep_cols = [seg_id_col, seg_name_col, emp24_col, emp34_col] + ([stage_col] if stage_col else [])
    df = df[keep_cols].copy()
    df = df.rename(columns={
        seg_id_col: "segment_id",
        seg_name_col: "segment_name",
        emp24_col: "emp_2024",
        emp34_col: "emp_2034",
        **({stage_col: "stage"} if stage_col else {})
    })

    # Types
    df["segment_id"] = pd.to_numeric(df["segment_id"], errors="coerce").astype("Int64")
    df["emp_2024"] = _coerce_num(df["emp_2024"])
    df["emp_2034"] = _coerce_num(df["emp_2034"])

    # Deduplicate
    df = df.dropna(subset=["segment_id"]).drop_duplicates(subset=["segment_id"])
    df["segment_id"] = df["segment_id"].astype(int)
    return df.reset_index(drop=True)

def _compute_cagr(emp24: float, emp34: float) -> float | None:
    """Return CAGR as decimal (e.g., 0.0123 for 1.23%)."""
    if emp24 is None or emp34 is None:
        return None
    if pd.isna(emp24) or pd.isna(emp34) or emp24 <= 0:
        return None
    try:
        return (float(emp34) / float(emp24)) ** (1.0 / (Y_END - Y_START)) - 1.0
    except Exception:
        return None

def _expand_yoy_timeseries(keys: dict, cagr_dec: float) -> pd.DataFrame:
    """
    Make rows years 2025..2034 with employment_yoy_pct in percent units.
    keys: e.g., {"segment_id": 1, "segment_name": "..."} or {"stage": "Upstream"}
    """
    if cagr_dec is None or math.isnan(cagr_dec):
        # emit NaNs to preserve shape; consumer can drop later if desired
        return pd.DataFrame([{**keys, "year": y, "employment_yoy_pct": pd.NA} for y in YEARS_YOY])
    pct = cagr_dec * 100.0
    return pd.DataFrame([{**keys, "year": y, "employment_yoy_pct": pct} for y in YEARS_YOY])

def main() -> None:
    bls = _read_bls_source()
    # Ensure stage present; if not, map from lookup
    bls = _ensure_stage(bls)

    # -----------------
    # SEGMENT-LEVEL YoY
    # -----------------
    seg_rows = []
    for _, r in bls.iterrows():
        cagr = _compute_cagr(r["emp_2024"], r["emp_2034"])
        seg_rows.append(_expand_yoy_timeseries(
            {"segment_id": int(r["segment_id"]), "segment_name": str(r["segment_name"])},
            cagr
        ))
    seg_yoy = pd.concat(seg_rows, ignore_index=True) if seg_rows else pd.DataFrame(
        columns=["segment_id", "segment_name", "year", "employment_yoy_pct"]
    )
    seg_yoy = seg_yoy.sort_values(["segment_id", "year"]).reset_index(drop=True)
    seg_yoy.to_csv(OUT_SEG, index=False)

    # ---------------
    # STAGE-LEVEL YoY
    # ---------------
    # Aggregate 2024/2034 across segments per stage, then compute stage CAGR
    stg_sum = bls.groupby("stage", as_index=False).agg(emp_2024=("emp_2024", "sum"),
                                                       emp_2034=("emp_2034", "sum"))
    stg_rows = []
    for _, r in stg_sum.iterrows():
        cagr = _compute_cagr(r["emp_2024"], r["emp_2034"])
        stg_rows.append(_expand_yoy_timeseries({"stage": str(r["stage"])}, cagr))
    stg_yoy = pd.concat(stg_rows, ignore_index=True) if stg_rows else pd.DataFrame(
        columns=["stage", "year", "employment_yoy_pct"]
    )
    # Stage ordering helpful for downstream plots
    stage_order = pd.CategoricalDtype(categories=["Upstream", "OEM", "Downstream"], ordered=True)
    if "stage" in stg_yoy.columns:
        stg_yoy["stage"] = stg_yoy["stage"].astype(str).astype(stage_order)
        stg_yoy = stg_yoy.sort_values(["stage", "year"]).reset_index(drop=True)
    stg_yoy.to_csv(OUT_STG, index=False)

    print(f"Wrote: {OUT_SEG}  (rows={len(seg_yoy)})")
    print(f"Wrote: {OUT_STG}  (rows={len(stg_yoy)})")

if __name__ == "__main__":
    main()
