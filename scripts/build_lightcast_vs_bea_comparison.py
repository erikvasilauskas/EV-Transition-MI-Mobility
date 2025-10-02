
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

# ---- Inputs: Lightcast (coreauto) ----
LC_SEG_BASE = DATA_INTERIM   / "mi_qcew_segment_employment_timeseries_coreauto.csv"
LC_STG_BASE = DATA_INTERIM   / "mi_qcew_stage_employment_timeseries_coreauto.csv"
LC_SEG_CMP  = DATA_PROCESSED / "mi_qcew_segment_employment_timeseries_coreauto_extended_compare.csv"
LC_STG_CMP  = DATA_PROCESSED / "mi_qcew_stage_employment_timeseries_coreauto_extended_compare.csv"

# ---- Inputs: BEA ----
BEA_SEG_BASE = DATA_INTERIM   / "mi_qcew_segment_employment_timeseries_bea.csv"
BEA_STG_BASE = DATA_INTERIM   / "mi_qcew_stage_employment_timeseries_bea.csv"
BEA_SEG_CMP  = DATA_PROCESSED / "mi_qcew_segment_employment_timeseries_bea_extended_compare.csv"
BEA_STG_CMP  = DATA_PROCESSED / "mi_qcew_stage_employment_timeseries_bea_extended_compare.csv"

# ---- Outputs ----
OUT_SEG_ALL = DATA_PROCESSED / "mi_qcew_segment_employment_timeseries_lightcast_vs_bea_compare.csv"
OUT_STG_ALL = DATA_PROCESSED / "mi_qcew_stage_employment_timeseries_lightcast_vs_bea_compare.csv"


def _require_exists(p: Path, label: str):
    if not p.exists():
        raise FileNotFoundError(f"Missing {label}: {p}")


def _coerce_year(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    df = df.dropna(subset=["year"]).copy()
    df["year"] = df["year"].astype(int)
    return df


def _standardize_segment_name(df: pd.DataFrame) -> pd.DataFrame:
    # Normalize to `segment_name` (accept either 'segment_name' or 'segment_label')
    if "segment_name" in df.columns:
        return df.rename(columns={"segment_name": "segment_name"})
    if "segment_label" in df.columns:
        df = df.rename(columns={"segment_label": "segment_name"})
    return df


def load_inputs():
    # Ensure presence
    _require_exists(LC_SEG_BASE, "Lightcast segment baseline")
    _require_exists(LC_STG_BASE, "Lightcast stage baseline")
    _require_exists(LC_SEG_CMP,  "Lightcast segment compare (extensions)")
    _require_exists(LC_STG_CMP,  "Lightcast stage compare (extensions)")

    _require_exists(BEA_SEG_BASE, "BEA segment baseline")
    _require_exists(BEA_STG_BASE, "BEA stage baseline")
    _require_exists(BEA_SEG_CMP,  "BEA segment compare (extensions)")
    _require_exists(BEA_STG_CMP,  "BEA stage compare (extensions)")

    # Load
    lc_seg_base = pd.read_csv(LC_SEG_BASE)
    lc_stg_base = pd.read_csv(LC_STG_BASE)
    lc_seg_cmp  = pd.read_csv(LC_SEG_CMP)
    lc_stg_cmp  = pd.read_csv(LC_STG_CMP)

    bea_seg_base = pd.read_csv(BEA_SEG_BASE)
    bea_stg_base = pd.read_csv(BEA_STG_BASE)
    bea_seg_cmp  = pd.read_csv(BEA_SEG_CMP)
    bea_stg_cmp  = pd.read_csv(BEA_STG_CMP)

    # Coerce years
    for df in (lc_seg_base, lc_stg_base, lc_seg_cmp, lc_stg_cmp,
               bea_seg_base, bea_stg_base, bea_seg_cmp, bea_stg_cmp):
        df = _coerce_year(df)

    return lc_seg_base, lc_stg_base, lc_seg_cmp, lc_stg_cmp, bea_seg_base, bea_stg_base, bea_seg_cmp, bea_stg_cmp


def build_segment_compare(lc_base: pd.DataFrame, lc_cmp: pd.DataFrame,
                          bea_base: pd.DataFrame, bea_cmp: pd.DataFrame) -> pd.DataFrame:
    # Baselines
    lc_b = _standardize_segment_name(lc_base.copy())
    lc_b = lc_b.assign(value_type="QCEW", forecast_source=None, applied_yoy_pct=pd.NA,
                       adjustment_source="Lightcast")
    bea_b = _standardize_segment_name(bea_base.copy())
    bea_b = bea_b.assign(value_type="QCEW", forecast_source=None, applied_yoy_pct=pd.NA,
                         adjustment_source="BEA")

    # Extensions
    lc_e = _standardize_segment_name(lc_cmp.copy())
    lc_e = lc_e.assign(adjustment_source="Lightcast")
    bea_e = _standardize_segment_name(bea_cmp.copy())
    bea_e = bea_e.assign(adjustment_source="BEA")

    # Columns we want to keep
    keep = ["segment_id", "segment_name", "year", "employment_qcew",
            "value_type", "forecast_source", "applied_yoy_pct", "adjustment_source"]

    out = pd.concat([
        lc_b[keep], lc_e[keep],
        bea_b[keep], bea_e[keep]
    ], ignore_index=True)

    # Dedupe & sort
    out = out.drop_duplicates(subset=["segment_id", "year", "value_type", "forecast_source", "adjustment_source"])
    out = out.sort_values(["segment_id", "year", "adjustment_source", "forecast_source", "value_type"]).reset_index(drop=True)
    return out


def build_stage_compare(lc_base: pd.DataFrame, lc_cmp: pd.DataFrame,
                        bea_base: pd.DataFrame, bea_cmp: pd.DataFrame) -> pd.DataFrame:
    # Baselines
    lc_b = lc_base.copy().assign(value_type="QCEW", forecast_source=None, applied_yoy_pct=pd.NA, adjustment_source="Lightcast")
    bea_b = bea_base.copy().assign(value_type="QCEW", forecast_source=None, applied_yoy_pct=pd.NA, adjustment_source="BEA")
    # Extensions
    lc_e = lc_cmp.copy().assign(adjustment_source="Lightcast")
    bea_e = bea_cmp.copy().assign(adjustment_source="BEA")

    keep = ["stage", "year", "employment_qcew",
            "value_type", "forecast_source", "applied_yoy_pct", "adjustment_source"]

    out = pd.concat([
        lc_b[keep], lc_e[keep],
        bea_b[keep], bea_e[keep]
    ], ignore_index=True)

    out = out.drop_duplicates(subset=["stage", "year", "value_type", "forecast_source", "adjustment_source"])
    out = out.sort_values(["stage", "year", "adjustment_source", "forecast_source", "value_type"]).reset_index(drop=True)
    return out

def add_segment_total(seg_df: pd.DataFrame) -> pd.DataFrame:
    """
    Append a 'Total (All Segments)' row per (year, value_type, forecast_source, adjustment_source).
    Leaves applied_yoy_pct as NA for totals.
    """
    base_keys = ["year", "value_type", "forecast_source", "adjustment_source"]
    totals = (
        seg_df.groupby(base_keys, as_index=False)["employment_qcew"]
              .sum(min_count=1)
    )
    totals["segment_id"] = 0
    totals["segment_name"] = "Total (All Segments)"
    totals["applied_yoy_pct"] = pd.NA

    # Reorder to match seg_df columns and append
    totals = totals[seg_df.columns]
    out = pd.concat([seg_df, totals], ignore_index=True)

    # Keep 'Total' last in sorts
    out["__seg_order"] = (out["segment_id"] == 0).astype(int)
    out = out.sort_values(["__seg_order", "segment_id", "year",
                           "adjustment_source", "forecast_source", "value_type"]).drop(columns="__seg_order")
    return out.reset_index(drop=True)


def add_stage_total(stg_df: pd.DataFrame) -> pd.DataFrame:
    """
    Append a 'Total' stage row per (year, value_type, forecast_source, adjustment_source).
    Leaves applied_yoy_pct as NA for totals.
    """
    base_keys = ["year", "value_type", "forecast_source", "adjustment_source"]
    totals = (
        stg_df.groupby(base_keys, as_index=False)["employment_qcew"]
              .sum(min_count=1)
    )
    totals["stage"] = "Total"
    totals["applied_yoy_pct"] = pd.NA

    totals = totals[stg_df.columns]
    out = pd.concat([stg_df, totals], ignore_index=True)

    # Keep 'Total' last in sorts
    out["__stg_order"] = (out["stage"] == "Total").astype(int)
    out = out.sort_values(["__stg_order", "stage", "year",
                           "adjustment_source", "forecast_source", "value_type"]).drop(columns="__stg_order")
    return out.reset_index(drop=True)


def main():
    (lc_seg_base, lc_stg_base, lc_seg_cmp, lc_stg_cmp,
     bea_seg_base, bea_stg_base, bea_seg_cmp, bea_stg_cmp) = load_inputs()

    # Re-coerce years after load (ensure in-place change sticks)
    for name, df in {
        "lc_seg_base": lc_seg_base, "lc_stg_base": lc_stg_base, "lc_seg_cmp": lc_seg_cmp, "lc_stg_cmp": lc_stg_cmp,
        "bea_seg_base": bea_seg_base, "bea_stg_base": bea_stg_base, "bea_seg_cmp": bea_seg_cmp, "bea_stg_cmp": bea_stg_cmp
    }.items():
        df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
        df.dropna(subset=["year"], inplace=True)
        df["year"] = df["year"].astype(int)

    seg_all = build_segment_compare(lc_seg_base, lc_seg_cmp, bea_seg_base, bea_seg_cmp)
    stg_all = build_stage_compare(lc_stg_base, lc_stg_cmp, bea_stg_base, bea_stg_cmp)
    
    seg_all = add_segment_total(seg_all)
    stg_all = add_stage_total(stg_all)

    seg_all.to_csv(OUT_SEG_ALL, index=False)
    stg_all.to_csv(OUT_STG_ALL, index=False)

    print(f"Wrote: {OUT_SEG_ALL}")
    print(f"Wrote: {OUT_STG_ALL}")


if __name__ == "__main__":
    main()
