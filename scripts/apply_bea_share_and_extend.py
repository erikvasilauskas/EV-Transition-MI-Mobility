
# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
import warnings
import re
import pandas as pd

warnings.filterwarnings("ignore", message="Workbook contains no default style", module="openpyxl")

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent

RAW_QCEW_PATH = REPO_ROOT / "data" / "raw" / "MI-QCEW-38-NAICS-2001-2024.xlsx"
BEA_PATH      = REPO_ROOT / "data" / "raw" / "auto_attribution_bea.csv"
SEGMENT_LOOKUP_PATH = REPO_ROOT / "data" / "lookups" / "segment_assignments.csv"

DATA_INTERIM   = REPO_ROOT / "data" / "interim"
DATA_PROCESSED = REPO_ROOT / "data" / "processed"
DATA_INTERIM.mkdir(parents=True, exist_ok=True)
DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

YOY_MOODY_SEG_MI = DATA_INTERIM / "moodys_michigan_segments_timeseries_yoy.csv"
YOY_MOODY_STG_MI = DATA_INTERIM / "moodys_michigan_stages_timeseries_yoy.csv"
YOY_BLS_SEG_US   = DATA_INTERIM / "bls_us_segments_timeseries_yoy.csv"
YOY_BLS_STG_US   = DATA_INTERIM / "bls_us_stages_timeseries_yoy.csv"

OUT_SEG_MI_ADJ   = DATA_INTERIM / "mi_qcew_segment_employment_timeseries_bea.csv"
OUT_STG_MI_ADJ   = DATA_INTERIM / "mi_qcew_stage_employment_timeseries_bea.csv"
OUT_NAICS_MI_ADJ = DATA_INTERIM / "mi_qcew_naics_bea_timeseries.csv"
OUT_SEG_MI_DIAG  = DATA_INTERIM / "mi_qcew_segment_bea_diagnostics.csv"
OUT_STG_MI_DIAG  = DATA_INTERIM / "mi_qcew_stage_bea_diagnostics.csv"

OUT_SEG_MI_MOODY = DATA_PROCESSED / "mi_qcew_segment_employment_timeseries_bea_extended_moody.csv"
OUT_STG_MI_MOODY = DATA_PROCESSED / "mi_qcew_stage_employment_timeseries_bea_extended_moody.csv"
OUT_SEG_MI_BLS   = DATA_PROCESSED / "mi_qcew_segment_employment_timeseries_bea_extended_bls.csv"
OUT_STG_MI_BLS   = DATA_PROCESSED / "mi_qcew_stage_employment_timeseries_bea_extended_bls.csv"

OUT_SEG_MI_COMPARE = DATA_PROCESSED / "mi_qcew_segment_employment_timeseries_bea_extended_compare.csv"
OUT_STG_MI_COMPARE = DATA_PROCESSED / "mi_qcew_stage_employment_timeseries_bea_extended_compare.csv"

def _require_exists(p: Path, label: str):
    if not p.exists():
        raise FileNotFoundError(f"Missing {label}: {p}")

def load_qcew_long() -> pd.DataFrame:
    _require_exists(RAW_QCEW_PATH, "MI QCEW workbook")
    wide = pd.read_excel(RAW_QCEW_PATH, skiprows=3).rename(columns={"Series ID": "series_id"})
    year_map = {}
    for col in wide.columns:
        if isinstance(col, str) and col.startswith("Annual"):
            try:
                year_map[col] = int(col.split("\n")[-1])
            except Exception:
                pass
    keep = ["series_id", *year_map.keys()]
    if "series_id" not in wide.columns:
        raise KeyError("QCEW missing 'Series ID'")
    long_df = wide[keep].melt(id_vars="series_id", value_vars=year_map.keys(),
                              var_name="year_lbl", value_name="employment")
    long_df["year"] = long_df["year_lbl"].map(year_map)
    long_df.drop(columns=["year_lbl"], inplace=True)
    long_df["employment"] = pd.to_numeric(long_df["employment"], errors="coerce")
    long_df["naics_code"] = long_df["series_id"].astype(str).str.extract(r"(\d{4})$")[0]
    long_df = long_df.dropna(subset=["naics_code", "employment"]).copy()
    long_df["naics_code"] = long_df["naics_code"].astype(str)
    long_df["year"] = pd.to_numeric(long_df["year"], errors="coerce").astype("Int64")
    long_df = long_df.dropna(subset=["year"]).copy()
    long_df["year"] = long_df["year"].astype(int)
    return long_df[["naics_code", "year", "employment"]]

def read_bea_shares() -> pd.DataFrame:
    _require_exists(BEA_PATH, "BEA attribution CSV")
    df = pd.read_csv(BEA_PATH)
    naics_col = next((c for c in df.columns if re.search(r"naics", str(c), re.I)), None)
    if naics_col is None:
        raise KeyError("BEA CSV: Could not find a NAICS column.")
    share_col = next((c for c in df.columns if re.search(r"bea_share_to_set", str(c), re.I)), None)
    if share_col is None:
        raise KeyError("BEA CSV missing 'bea_share_to_set' column.")
    out = df[[naics_col, share_col]].copy()
    out[naics_col] = out[naics_col].astype(str).str.extract(r"(\d{4,6})")[0].str[:4]
    s = out[share_col].astype(str).str.strip().str.replace("%", "", regex=False)
    num = pd.to_numeric(s, errors="coerce")
    num = num.where(num <= 1, num / 100.0)
    out["bea_share_to_set"] = num.clip(0, 1)
    shares4 = (out.groupby(naics_col, as_index=False)["bea_share_to_set"]
                 .mean()
                 .rename(columns={naics_col: "naics_code"}))
    if shares4.empty or shares4["bea_share_to_set"].isna().all():
        raise ValueError("Parsed BEA shares are empty/NaN; check input formatting.")
    return shares4

def load_segment_lookup() -> pd.DataFrame:
    _require_exists(SEGMENT_LOOKUP_PATH, "segment lookup")
    lk = pd.read_csv(SEGMENT_LOOKUP_PATH, dtype={"naics_code": str}).drop_duplicates("naics_code")
    need = {"naics_code", "segment_id", "segment_name", "stage"}
    missing = need - set(lk.columns)
    if missing:
        raise KeyError(f"Segment lookup missing columns: {missing}")
    lk["segment_id"] = pd.to_numeric(lk["segment_id"], errors="raise").astype(int)
    lk["segment_name"] = lk["segment_name"].astype(str)
    lk["stage"] = lk["stage"].astype(str)
    return lk[["naics_code", "segment_id", "segment_name", "stage"]]

def apply_bea_share(qcew_long: pd.DataFrame, shares4: pd.DataFrame) -> pd.DataFrame:
    merged = qcew_long.merge(shares4, on="naics_code", how="left")
    merged["bea_share_to_set"] = pd.to_numeric(merged["bea_share_to_set"], errors="coerce").fillna(0.0)
    merged = merged.rename(columns={"employment": "employment_qcew_raw"})
    merged["employment_adj"] = merged["employment_qcew_raw"] * merged["bea_share_to_set"]
    return merged

def _canon_label(seg_id: int, seg_name: str) -> str:
    base = (seg_name or "").split(" - ")[0].strip()
    prefix = f"{int(seg_id)}. "
    if base.startswith(prefix):
        return base
    return prefix + base if base else str(seg_id)

def aggregate_adjusted(naics_df: pd.DataFrame, lookup: pd.DataFrame):
    m = naics_df.merge(lookup, on="naics_code", how="left", validate="many_to_one")
    if m[["segment_id", "segment_name", "stage"]].isna().any().any():
        miss = sorted(m.loc[m[["segment_id","segment_name","stage"]].isna().any(axis=1), "naics_code"].unique())
        raise ValueError(f"Missing segment mapping for NAICS codes: {miss}")
    m["segment_label"] = m.apply(lambda r: _canon_label(r["segment_id"], r["segment_name"]), axis=1)
    seg = (m.groupby(["segment_id", "segment_label", "year"], as_index=False)["employment_adj"]
             .sum(min_count=1)
             .rename(columns={"employment_adj": "employment_qcew", "segment_label": "segment_name"})
             .sort_values(["segment_id", "year"])
             .reset_index(drop=True))
    stg = (m.groupby(["stage", "year"], as_index=False)["employment_adj"]
             .sum(min_count=1)
             .rename(columns={"employment_adj": "employment_qcew"})
             .sort_values(["stage", "year"])
             .reset_index(drop=True))
    return seg, stg, m

def clean_yoy_segments(df: pd.DataFrame) -> pd.DataFrame:
    need = {"segment_id", "year", "employment_yoy_pct"}
    missing = need - set(df.columns)
    if missing:
        raise ValueError(f"Segments YoY missing columns: {missing}")
    out = df.copy()
    out["segment_id"] = pd.to_numeric(out["segment_id"], errors="coerce").astype("Int64")
    out["year"] = pd.to_numeric(out["year"], errors="coerce").astype("Int64")
    out = out.dropna(subset=["segment_id", "year"])
    out["segment_id"] = out["segment_id"].astype(int)
    out["year"] = out["year"].astype(int)
    out["employment_yoy_pct"] = pd.to_numeric(out["employment_yoy_pct"], errors="coerce")
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
    out["year"] = pd.to_numeric(out["year"], errors="coerce").astype("Int64")
    out = out.dropna(subset=["year"]).copy()
    out["year"] = out["year"].astype(int)
    out["employment_yoy_pct"] = pd.to_numeric(out["employment_yoy_pct"], errors="coerce")
    return out[["stage", "year", "employment_yoy_pct"]].drop_duplicates(subset=["stage", "year"]).sort_values(["stage", "year"]).reset_index(drop=True)

def extend_segments_with_yoy(baseline: pd.DataFrame, yoy: pd.DataFrame, source_name: str) -> pd.DataFrame:
    pieces = []
    hist = baseline.copy()
    hist["value_type"] = "QCEW"
    hist["forecast_source"] = None
    hist["applied_yoy_pct"] = pd.NA
    pieces.append(hist)
    for seg_id, g in baseline.groupby("segment_id", as_index=False):
        last_year = int(g["year"].max())
        last_level = float(g.loc[g["year"].idxmax(), "employment_qcew"])
        seg_name = g.get("segment_name", pd.Series([None])).dropna().iloc[0] if "segment_name" in g.columns else None
        yy = yoy[yoy["segment_id"] == seg_id]
        if yy.empty:
            continue
        cur = last_level
        rows = []
        for y in sorted(yy["year"].unique()):
            if y <= last_year:
                continue
            rate = yy.loc[yy["year"] == y, "employment_yoy_pct"].iloc[0]
            if pd.isna(rate):
                continue
            cur *= (1.0 + float(rate) / 100.0)
            rows.append({
                "segment_id": seg_id,
                "segment_name": seg_name if seg_name is not None else (yy["segment_name"].iloc[0] if "segment_name" in yy.columns else None),
                "year": y,
                "employment_qcew": cur,
                "value_type": "Forecast",
                "forecast_source": source_name,
                "applied_yoy_pct": rate,
            })
        if rows:
            pieces.append(pd.DataFrame(rows))
    out = pd.concat(pieces, ignore_index=True)
    out["pref"] = out["value_type"].map({"QCEW": 0, "Forecast": 1})
    out = out.sort_values(["segment_id", "year", "pref"]).drop_duplicates(subset=["segment_id", "year"], keep="first").drop(columns=["pref"])
    return out.sort_values(["segment_id", "year"]).reset_index(drop=True)

def extend_stages_with_yoy(baseline: pd.DataFrame, yoy: pd.DataFrame, source_name: str) -> pd.DataFrame:
    pieces = []
    hist = baseline.copy()
    hist["value_type"] = "QCEW"
    hist["forecast_source"] = None
    hist["applied_yoy_pct"] = pd.NA
    pieces.append(hist)
    for st, g in baseline.groupby("stage", as_index=False):
        last_year = int(g["year"].max())
        last_level = float(g.loc[g["year"].idxmax(), "employment_qcew"])
        yy = yoy[yoy["stage"] == st]
        if yy.empty:
            continue
        cur = last_level
        rows = []
        for y in sorted(yy["year"].unique()):
            if y <= last_year:
                continue
            rate = yy.loc[yy["year"] == y, "employment_yoy_pct"].iloc[0]
            if pd.isna(rate):
                continue
            cur *= (1.0 + float(rate) / 100.0)
            rows.append({
                "stage": st,
                "year": y,
                "employment_qcew": cur,
                "value_type": "Forecast",
                "forecast_source": source_name,
                "applied_yoy_pct": rate,
            })
        if rows:
            pieces.append(pd.DataFrame(rows))
    out = pd.concat(pieces, ignore_index=True)
    out["pref"] = out["value_type"].map({"QCEW": 0, "Forecast": 1})
    out = out.sort_values(["stage", "year", "pref"]).drop_duplicates(subset=["stage", "year"], keep="first").drop(columns=["pref"])
    return out.sort_values(["stage", "year"]).reset_index(drop=True)

def main() -> None:
    qcew_long = load_qcew_long()
    shares4 = read_bea_shares()
    lookup = load_segment_lookup()

    match = qcew_long.merge(shares4, on="naics_code", how="left")
    match_rate = match["bea_share_to_set"].notna().mean()
    print(f"BEA share match rate: {match_rate:.1%} over {match['naics_code'].nunique()} NAICS-4")

    qcew_adj_naics = apply_bea_share(qcew_long, shares4)
    seg_adj, stg_adj, m_all = aggregate_adjusted(qcew_adj_naics, lookup)

    m_for_audit = m_all[[
        "naics_code", "segment_id", "segment_name", "stage", "year",
        "employment_qcew_raw", "bea_share_to_set", "employment_adj"
    ]].sort_values(["segment_id", "naics_code", "year"])
    m_for_audit.to_csv(OUT_NAICS_MI_ADJ, index=False)
    print(f"Wrote NAICS audit with BEA shares -> {OUT_NAICS_MI_ADJ}")

    seg_adj.to_csv(OUT_SEG_MI_ADJ, index=False)
    stg_adj.to_csv(OUT_STG_MI_ADJ, index=False)
    print(f"Wrote BEA-adjusted baselines:\n  {OUT_SEG_MI_ADJ}\n  {OUT_STG_MI_ADJ}")

    seg_diag = (
        m_for_audit.groupby(["segment_id", "segment_name", "year"], as_index=False)
          .agg(
              employment_qcew_raw=("employment_qcew_raw", "sum"),
              employment_bea=("employment_adj", "sum"),
              naics_count=("naics_code", "nunique"),
              share_min=("bea_share_to_set", "min"),
              share_max=("bea_share_to_set", "max"),
          )
    )
    seg_diag["share_weighted"] = seg_diag["employment_bea"] / seg_diag["employment_qcew_raw"].replace({0: pd.NA})

    stg_diag = (
        m_for_audit.groupby(["stage", "year"], as_index=False)
          .agg(
              employment_qcew_raw=("employment_qcew_raw", "sum"),
              employment_bea=("employment_adj", "sum"),
              naics_count=("naics_code", "nunique"),
              share_min=("bea_share_to_set", "min"),
              share_max=("bea_share_to_set", "max"),
          )
    )
    stg_diag["share_weighted"] = stg_diag["employment_bea"] / stg_diag["employment_qcew_raw"].replace({0: pd.NA})

    seg_diag.to_csv(OUT_SEG_MI_DIAG, index=False)
    stg_diag.to_csv(OUT_STG_MI_DIAG, index=False)
    print(f"Wrote diagnostics -> {OUT_SEG_MI_DIAG}, {OUT_STG_MI_DIAG}")

    if (seg_diag["share_weighted"] > 1).any() or (stg_diag["share_weighted"] > 1).any():
        print("WARNING: weighted share > 1 detected — audit BEA shares.")

    # Growth rates
    _require_exists(YOY_MOODY_SEG_MI, "Moody segments YoY (MI)")
    _require_exists(YOY_MOODY_STG_MI, "Moody stages YoY (MI)")
    _require_exists(YOY_BLS_SEG_US,   "BLS segments YoY (US)")
    _require_exists(YOY_BLS_STG_US,   "BLS stages YoY (US)")

    moody_seg = clean_yoy_segments(pd.read_csv(YOY_MOODY_SEG_MI))
    moody_stg = clean_yoy_stages(pd.read_csv(YOY_MOODY_STG_MI))
    bls_seg   = clean_yoy_segments(pd.read_csv(YOY_BLS_SEG_US))
    bls_stg   = clean_yoy_stages(pd.read_csv(YOY_BLS_STG_US))

    seg_moody = extend_segments_with_yoy(seg_adj, moody_seg, "Moody")
    stg_moody = extend_stages_with_yoy(stg_adj, moody_stg, "Moody")
    seg_bls   = extend_segments_with_yoy(seg_adj, bls_seg, "BLS")
    stg_bls   = extend_stages_with_yoy(stg_adj, bls_stg, "BLS")

    seg_moody.to_csv(OUT_SEG_MI_MOODY, index=False)
    stg_moody.to_csv(OUT_STG_MI_MOODY, index=False)
    seg_bls.to_csv(OUT_SEG_MI_BLS, index=False)
    stg_bls.to_csv(OUT_STG_MI_BLS, index=False)
    print(f"Wrote extended files:\n  {OUT_SEG_MI_MOODY}\n  {OUT_STG_MI_MOODY}\n  {OUT_SEG_MI_BLS}\n  {OUT_STG_MI_BLS}")

    seg_common = ["segment_id", "segment_name", "year", "employment_qcew", "value_type", "forecast_source", "applied_yoy_pct"]
    stg_common = ["stage", "year", "employment_qcew", "value_type", "forecast_source", "applied_yoy_pct"]

    seg_cmp = pd.concat([seg_moody[seg_common], seg_bls[seg_common]], ignore_index=True).sort_values(["segment_id", "year", "forecast_source", "value_type"])
    seg_cmp = seg_cmp.drop_duplicates(subset=["segment_id", "year", "value_type", "forecast_source"], keep="first")
    stg_cmp = pd.concat([stg_moody[stg_common], stg_bls[stg_common]], ignore_index=True).sort_values(["stage", "year", "forecast_source", "value_type"])
    stg_cmp = stg_cmp.drop_duplicates(subset=["stage", "year", "value_type", "forecast_source"], keep="first")

    seg_cmp.to_csv(OUT_SEG_MI_COMPARE, index=False)
    stg_cmp.to_csv(OUT_STG_MI_COMPARE, index=False)
    print(f"Wrote comparison stacks:\n  {OUT_SEG_MI_COMPARE}\n  {OUT_STG_MI_COMPARE}")

if __name__ == "__main__":
    main()
