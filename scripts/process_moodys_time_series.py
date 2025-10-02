# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
import warnings
import re
import pandas as pd

# Silence benign openpyxl style warning
warnings.filterwarnings(
    "ignore",
    message="Workbook contains no default style",
    module="openpyxl",
)

# ---------- Repo-relative paths ----------
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent

RAW_XLSX = REPO_ROOT / "data" / "raw" / "Moody's Supply Chain Employment and Output 1970-2055.xlsx"
SEGMENT_LOOKUP_PATH = REPO_ROOT / "data" / "lookups" / "segment_assignments.csv"

OUT_DIR = REPO_ROOT / "data" / "interim"
OUT_DIR.mkdir(parents=True, exist_ok=True)

OUT_SEG_MI = OUT_DIR / "moodys_michigan_segments_timeseries.csv"
OUT_SEG_US = OUT_DIR / "moodys_us_segments_timeseries.csv"
OUT_STG_MI = OUT_DIR / "moodys_michigan_stages_timeseries.csv"
OUT_STG_US = OUT_DIR / "moodys_us_stages_timeseries.csv"
OUT_SEG_MI_YOY = OUT_DIR / "moodys_michigan_segments_timeseries_yoy.csv"
OUT_SEG_US_YOY = OUT_DIR / "moodys_us_segments_timeseries_yoy.csv"
OUT_STG_MI_YOY = OUT_DIR / "moodys_michigan_stages_timeseries_yoy.csv"
OUT_STG_US_YOY = OUT_DIR / "moodys_us_stages_timeseries_yoy.csv"

# ---------- Config ----------
NAICS_OVERRIDES = {"4471": "4571"}  # e.g., legacy -> current gas stations
METRICS = ("employment", "wages", "gdp")  # we normalize "output"/"gdp" to gdp


def load_segment_lookup() -> pd.DataFrame:
    """Expect columns: naics_code, segment_id, segment_name, stage"""
    lk = pd.read_csv(SEGMENT_LOOKUP_PATH, dtype={"naics_code": str}).drop_duplicates("naics_code")
    req = {"naics_code", "segment_id", "segment_name", "stage"}
    missing = req - set(lk.columns)
    if missing:
        raise KeyError(f"Missing columns in segment lookup: {missing}")
    lk["segment_id"] = pd.to_numeric(lk["segment_id"], errors="raise").astype(int)
    lk["segment_name"] = lk["segment_name"].astype(str)
    lk["stage"] = lk["stage"].astype(str)
    return lk[["naics_code", "segment_id", "segment_name", "stage"]]


def infer_metric(desc: str) -> str:
    d = (desc or "").lower()
    if "employment" in d:
        return "employment"
    if "wage" in d or "earnings" in d or "compensation" in d:
        return "wages"
    if "output" in d or "gdp" in d or "gross" in d or "value added" in d:
        return "gdp"
    return "other"


def read_wide() -> pd.DataFrame:
    """
    Reads the single sheet with header row 0, where columns are:
      - 'Mnemonic:', 'Description:', 'Source:', 'Native Frequency:', 'Geography:'
      - year columns labeled as 'YYYY-12-31 00:00:00'
    """
    if not RAW_XLSX.exists():
        raise FileNotFoundError(f"Raw workbook not found: {RAW_XLSX}")

    df = pd.read_excel(RAW_XLSX, sheet_name=0, header=0)

    # Identify year columns by parseable year-end date headers
    year_cols = []
    for c in df.columns:
        s = str(c)
        # Fast-path for the exact format we saw
        if s.endswith("00:00:00") and "-" in s:
            try:
                ts = pd.to_datetime(s, errors="raise")
                if ts.month == 12 and ts.day == 31:
                    year_cols.append(c)
            except Exception:
                pass
        else:
            # Fallback: try parse any date-like header and keep year-ends
            try:
                ts = pd.to_datetime(s, errors="raise")
                if ts.month == 12 and ts.day == 31:
                    year_cols.append(c)
            except Exception:
                pass

    if not year_cols:
        raise ValueError("No year-end date columns found (expected 'YYYY-12-31 00:00:00').")

    # Keep only what we need
    keep = ["Mnemonic:", "Description:", "Geography:", *year_cols]
    missing = [k for k in keep[:3] if k not in df.columns]
    if missing:
        raise KeyError(f"Missing required attribute column(s): {missing}")

    df = df[keep].copy()

    # Metric & NAICS
    df["metric"] = df["Description:"].astype(str).map(infer_metric)
    df = df[df["metric"].isin(METRICS)].copy()

    df["naics_code"] = df["Mnemonic:"].astype(str).str.extract(r"(\d{4})")[0]
    df["naics_code"] = df["naics_code"].replace(NAICS_OVERRIDES)

    # Drop rows without NAICS or Geography
    df = df.dropna(subset=["naics_code", "Geography:"]).copy()
    df["naics_code"] = df["naics_code"].astype(str)

    return df, year_cols


def melt_to_long(df: pd.DataFrame, year_cols: list) -> pd.DataFrame:
    """
    Long format: one row per NAICS-year-metric with value column,
    then pivot metrics to columns: employment, wages, gdp
    """
    long = df.melt(
        id_vars=["naics_code", "metric", "Geography:"],
        value_vars=year_cols,
        var_name="date",
        value_name="value",
    )
    long["year"] = pd.to_datetime(long["date"]).dt.year
    long = long.drop(columns=["date"])

    # Pivot to metric columns
    long = long.pivot_table(
        index=["naics_code", "Geography:", "year"],
        columns="metric",
        values="value",
        aggfunc="first",
    ).reset_index()

    # Ensure all metric columns exist
    for m in METRICS:
        if m not in long.columns:
            long[m] = pd.NA

    # Sort nicely
    long = long.sort_values(["naics_code", "Geography:", "year"]).reset_index(drop=True)
    return long


def aggregate_timeseries(naics_long: pd.DataFrame, lookup: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    """
    Sum employment, wages, gdp by group_cols + year.
    group_cols examples:
      - ["segment_id", "segment_name"]
      - ["stage"]
    """
    df = naics_long.merge(lookup, on="naics_code", how="left", validate="many_to_one")
    if df[group_cols].isna().any().any():
        missing = sorted(df.loc[df[group_cols].isna().any(axis=1), "naics_code"].unique())
        raise ValueError(f"Segment lookup missing for NAICS codes: {missing}")

    grouped = (
        df.groupby(group_cols + ["year"], as_index=False)[list(METRICS)]
          .sum(min_count=1)
    )
    return grouped.sort_values(group_cols + ["year"]).reset_index(drop=True)

def compute_yoy_pct(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    """
    Compute year-over-year % change for employment, wages, gdp by group and calendar year.
    Returns columns: group_cols + ['year', 'employment_yoy_pct', 'wages_yoy_pct', 'gdp_yoy_pct'].
    """
    metrics = ["employment", "wages", "gdp"]
    out = []

    for keys, g in df.groupby(group_cols, dropna=False):
        years_present = sorted(g["year"].unique())
        if not years_present:
            continue

        # Reindex to a continuous year index so t-1 is truly previous calendar year
        idx = range(min(years_present), max(years_present) + 1)
        g2 = g.set_index("year").reindex(idx)
        # Ensure numeric
        for m in metrics:
            g2[m] = pd.to_numeric(g2[m], errors="coerce")

        # Compute YoY = (t - t-1) / (t-1) * 100, but leave NaN when prior is 0 or missing
        for m in metrics:
            prev = g2[m].shift(1)
            yoy = (g2[m] - prev) / prev * 100
            yoy[prev == 0] = pd.NA
            g2[m + "_yoy_pct"] = yoy

        # Keep only rows for years present in the original group
        keep = g2.loc[years_present, [m + "_yoy_pct" for m in metrics]].copy()
        keep.index.name = "year"
        keep = keep.reset_index()

        # Attach group key columns
        if isinstance(keys, tuple):
            for i, col in enumerate(group_cols):
                keep[col] = keys[i]
        else:
            keep[group_cols[0]] = keys

        cols = group_cols + ["year", "employment_yoy_pct", "wages_yoy_pct", "gdp_yoy_pct"]
        out.append(keep[cols])

    if not out:
        return pd.DataFrame(columns=group_cols + ["year", "employment_yoy_pct", "wages_yoy_pct", "gdp_yoy_pct"])

    res = pd.concat(out, ignore_index=True)
    return res.sort_values(group_cols + ["year"]).reset_index(drop=True)


def main() -> None:
    lookup = load_segment_lookup()
    wide, year_cols = read_wide()
    long_all = melt_to_long(wide, year_cols)

    # Split by geography (exact labels from the file)
    long_mi = long_all[long_all["Geography:"].eq("Michigan")].drop(columns=["Geography:"])
    long_us = long_all[long_all["Geography:"].eq("United States")].drop(columns=["Geography:"])

    # Segments
    seg_mi = aggregate_timeseries(long_mi, lookup, ["segment_id", "segment_name"])
    seg_us = aggregate_timeseries(long_us, lookup, ["segment_id", "segment_name"])
    
    # Force numeric prefix in-place (avoid double-prefixing)
    for df in (seg_mi, seg_us):
        df["segment_name"] = (
            df["segment_id"].astype(int).astype(str)
            + ". "
            + df["segment_name"].astype(str).str.replace(r"^\s*\d+\.\s*", "", regex=True)
        )
    
    # Stages
    stg_mi = aggregate_timeseries(long_mi, lookup, ["stage"])
    stg_us = aggregate_timeseries(long_us, lookup, ["stage"])

    # Write outputs
    seg_mi.to_csv(OUT_SEG_MI, index=False)
    seg_us.to_csv(OUT_SEG_US, index=False)
    stg_mi.to_csv(OUT_STG_MI, index=False)
    stg_us.to_csv(OUT_STG_US, index=False)
    
    # YoY % changes for segments
    seg_mi_yoy = compute_yoy_pct(seg_mi, ["segment_id", "segment_name"])
    seg_us_yoy = compute_yoy_pct(seg_us, ["segment_id", "segment_name"])

    # YoY % changes for stages
    stg_mi_yoy = compute_yoy_pct(stg_mi, ["stage"])
    stg_us_yoy = compute_yoy_pct(stg_us, ["stage"])

    # Write YoY outputs
    seg_mi_yoy.to_csv(OUT_SEG_MI_YOY, index=False)
    seg_us_yoy.to_csv(OUT_SEG_US_YOY, index=False)
    stg_mi_yoy.to_csv(OUT_STG_MI_YOY, index=False)
    stg_us_yoy.to_csv(OUT_STG_US_YOY, index=False)
    
    print(f"Wrote: {OUT_SEG_MI}")
    print(f"Wrote: {OUT_SEG_US}")
    print(f"Wrote: {OUT_STG_MI}")
    print(f"Wrote: {OUT_STG_US}")
    print(f"Wrote: {OUT_SEG_MI_YOY}")
    print(f"Wrote: {OUT_SEG_US_YOY}")
    print(f"Wrote: {OUT_STG_MI_YOY}")
    print(f"Wrote: {OUT_STG_US_YOY}")


if __name__ == "__main__":
    main()
