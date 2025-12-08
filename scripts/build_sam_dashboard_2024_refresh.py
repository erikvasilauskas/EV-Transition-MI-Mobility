"""Generate SAM-standard employment projections and occupation forecasts.

This script uses the Michigan SAM auto shares as the canonical adjustment
for upstream industries (plus NAICS 5413/5414/5417) and applies the
available projection rates to produce NAICS-, segment-, and stage-level
employment time series. It also prepares the inputs needed to run the
occupation forecast pipeline and invokes the existing
`occupation_forecasts_from_segment_totals.py` script with a custom output
prefix.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

import os
import numpy as np
import pandas as pd
import re
from process_moodys_time_series import read_wide


BASE_YEAR = 2024
# Set USE_MONTHLY_BASE = True and BASE_PERIOD if you want to override the base employment
# with a specific monthly QCEW snapshot (e.g., 2025-03-01). Default is annual 2024 QCEW.
USE_MONTHLY_BASE = False
BASE_PERIOD = None
MONTHLY_QCEW_PATH = Path("data/raw/qcew_auto_employment_monthly_clean.csv")
YEARS = list(range(BASE_YEAR, 2035))
TARGET_STAGE = {"upstream"}
TARGET_CHANGE_YEAR = 2030
OEM_NAICS = {"5413", "5414", "5417"}
ADJUSTMENT_SOURCE = "sam_mi"
BLS_SEGMENT_SUMMARY = Path("data/processed/us_staffing_segments_summary.csv")
UPSTREAM_CORE_STAGES = {"upstream", "oem"}
UPSTREAM_CORE_SEGMENT_ID = 11
UPSTREAM_CORE_SEGMENT_NAME = "Upstream + Core/OEM"
UPSTREAM_CORE_STAGE_LABEL = "Upstream + Core/OEM"
SEGMENT_LABELS = {
    1: "1. Materials & Processing",
    2: "2. Equipment Manufacturing",
    3: "3. Forging & Foundries",
    4: "4. Parts & Machining",
    5: "5. Component Systems",
    6: "6. Engineering & Design",
    7: "7. Core Automotive",
    8: "8. Motor Vehicle Parts, Materials, & Products Sales",
    9: "9. Dealers, Maintenance, & Repair",
    10: "10. Logistics",
    UPSTREAM_CORE_SEGMENT_ID: UPSTREAM_CORE_SEGMENT_NAME,
}

SEGMENT_CHANGE_STAGE_GROUPS = [
    {"key": "upstream", "name": "Upstream", "label": "Upstream (segments 1-5)", "segments": set(range(1, 6))},
    {"key": "core_oem", "name": "Core/OEM", "label": "Core/OEM (segments 6-7)", "segments": {6, 7}},
    {"key": "downstream", "name": "Downstream", "label": "Downstream (segments 8-10)", "segments": {8, 9, 10}},
    {
        "key": "upstream_core",
        "name": "Upstream + Core/OEM",
        "label": "Upstream + Core/OEM (segments 1-7)",
        "segments": set(range(1, 8)),
    },
    {
        "key": "all_segments",
        "name": "All Segments",
        "label": "All Segments (segments 1-10)",
        "segments": set(range(1, 11)),
    },
]

MAJOR_OCCUPATIONS = {
    "00": ("00-0000", "All Occupations"),
    "11": ("11-0000", "Management Occupations"),
    "13": ("13-0000", "Business and Financial Operations Occupations"),
    "15": ("15-0000", "Computer and Mathematical Occupations"),
    "17": ("17-0000", "Architecture and Engineering Occupations"),
    "19": ("19-0000", "Life, Physical, and Social Science Occupations"),
    "21": ("21-0000", "Community and Social Service Occupations"),
    "23": ("23-0000", "Legal Occupations"),
    "25": ("25-0000", "Educational Instruction and Library Occupations"),
    "27": ("27-0000", "Arts, Design, Entertainment, Sports, and Media Occupations"),
    "29": ("29-0000", "Healthcare Practitioners and Technical Occupations"),
    "31": ("31-0000", "Healthcare Support Occupations"),
    "33": ("33-0000", "Protective Service Occupations"),
    "35": ("35-0000", "Food Preparation and Serving Related Occupations"),
    "37": ("37-0000", "Building and Grounds Cleaning and Maintenance Occupations"),
    "39": ("39-0000", "Personal Care and Service Occupations"),
    "41": ("41-0000", "Sales and Related Occupations"),
    "43": ("43-0000", "Office and Administrative Support Occupations"),
    "45": ("45-0000", "Farming, Fishing, and Forestry Occupations"),
    "47": ("47-0000", "Construction and Extraction Occupations"),
    "49": ("49-0000", "Installation, Maintenance, and Repair Occupations"),
    "51": ("51-0000", "Production Occupations"),
    "53": ("53-0000", "Transportation and Material Moving Occupations"),
}


def load_monthly_base_lookup(path: Path, base_period: pd.Timestamp | None) -> dict[str, float]:
    """Optional monthly override for base employment; returns {} when disabled."""
    if not USE_MONTHLY_BASE or base_period is None:
        return {}
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_csv(path)
    if df.empty:
        return {}
    df["period"] = pd.to_datetime(df["period"], errors="coerce")
    df = df[(df["row_type"] == "naics_detail") & (df["period"] == base_period)].copy()
    if df.empty:
        return {}
    df["naics_code"] = df["naics_code"].astype(str).str.strip().str.zfill(4)
    df["employment"] = pd.to_numeric(df["employment"], errors="coerce")
    df = df.dropna(subset=["employment"])
    return df.set_index("naics_code")["employment"].to_dict()

ADVANCED_TRAINING_LEVELS = {
    "moderate-term on-the-job training",
    "long-term on-the-job training",
    "apprenticeship",
    "internship/residency",
}


def _clean_text(value: str | float | None) -> str:
    if isinstance(value, float) and np.isnan(value):
        return ""
    if value is None:
        return ""
    return str(value).strip().lower()


def derive_training_group(education: str | float | None, training: str | float | None) -> str:
    edu = _clean_text(education)
    training_clean = _clean_text(training)
    if edu.startswith("ba"):
        return "BA+"
    is_sc = "associate" in edu or "sc" in edu
    if is_sc:
        return "SC/Associate or Employer Training"
    if edu.startswith("hs") or "less" in edu:
        if training_clean in ADVANCED_TRAINING_LEVELS:
            return "SC/Associate or Employer Training"
        return "HS or Less - Limited Training"
    return "SC/Associate or Employer Training"


def _normalize_segment_name(name: str) -> str:
    if not isinstance(name, str):
        return ""
    cleaned = re.sub(r"^\d+\.\s*", "", name)
    cleaned = re.sub(r"[&,]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def build_segment_change_tables(
    segment_summary: pd.DataFrame,
    base_year: int = YEARS[0],
    target_year: int = TARGET_CHANGE_YEAR,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    valid_segments = set(range(1, 11))

    def _extract(year: int) -> pd.DataFrame:
        subset = segment_summary[
            (segment_summary["year"] == year) & (segment_summary["segment_id"].isin(valid_segments))
        ].copy()
        if subset.empty:
            return subset
        subset["segment_id"] = subset["segment_id"].astype(int)
        subset["segment_name"] = subset["segment_name"].astype(str)
        cols = [
            "projection_method",
            "projection_label",
            "segment_id",
            "segment_name",
            "employment_raw",
            "employment_auto",
        ]
        return subset[cols]

    base = _extract(base_year)
    target = _extract(target_year)
    if base.empty or target.empty:
        return pd.DataFrame(), pd.DataFrame()

    base = base.rename(columns={"employment_raw": "base_raw", "employment_auto": "base_auto"})
    target = target.rename(columns={"employment_raw": "target_raw", "employment_auto": "target_auto"})

    merged = base.merge(
        target,
        on=["projection_method", "projection_label", "segment_id", "segment_name"],
        how="inner",
    )
    if merged.empty:
        return pd.DataFrame(), pd.DataFrame()

    merged["forecast_source"] = merged["projection_method"]
    merged["raw_change"] = merged["target_raw"] - merged["base_raw"]
    merged["auto_change"] = merged["target_auto"] - merged["base_auto"]
    merged["segment_name_norm"] = merged["segment_name"].apply(_normalize_segment_name)
    merged["segment_label"] = merged["segment_id"].astype(str) + "-" + merged["segment_name_norm"]

    segment_cols = [
        "forecast_source",
        "projection_label",
        "segment_id",
        "segment_name_norm",
        "segment_label",
        "base_raw",
        "target_raw",
        "raw_change",
        "base_auto",
        "target_auto",
        "auto_change",
    ]
    segment_change = merged[segment_cols].sort_values(["forecast_source", "segment_id"]).reset_index(drop=True)

    stage_frames: list[pd.DataFrame] = []
    for order, group in enumerate(SEGMENT_CHANGE_STAGE_GROUPS):
        stage_subset = merged[merged["segment_id"].isin(group["segments"])]
        if stage_subset.empty:
            continue
        agg = (
            stage_subset
            .groupby(["forecast_source", "projection_label"], as_index=False)[
                ["base_raw", "target_raw", "base_auto", "target_auto"]
            ]
            .sum()
        )
        agg["raw_change"] = agg["target_raw"] - agg["base_raw"]
        agg["auto_change"] = agg["target_auto"] - agg["base_auto"]
        agg["stage_key"] = group["key"]
        agg["stage_name"] = group["name"]
        agg["stage_label"] = group["label"]
        agg["stage_order"] = order
        stage_frames.append(agg)

    if stage_frames:
        stage_change = pd.concat(stage_frames, ignore_index=True)
        stage_change.sort_values(["forecast_source", "stage_order"], inplace=True)
        stage_change.drop(columns=["stage_order"], inplace=True)
        stage_cols = [
            "forecast_source",
            "projection_label",
            "stage_key",
            "stage_name",
            "stage_label",
            "base_raw",
            "target_raw",
            "raw_change",
            "base_auto",
            "target_auto",
            "auto_change",
        ]
        stage_change = stage_change[stage_cols].reset_index(drop=True)
    else:
        stage_change = pd.DataFrame()

    return segment_change, stage_change


def _normalized_path(path: Path) -> str:
    path = Path(path).resolve()
    path_str = str(path)
    if os.name == "nt" and not path_str.startswith("\\\\?\\"):
        return "\\\\?\\" + path_str
    return path_str


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    target = _normalized_path(path)
    print(f"Writing CSV to {target}")
    with open(target, "w", newline="", encoding="utf-8") as fh:
        df.to_csv(fh, index=False)


def write_excel(df: pd.DataFrame, path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    target = _normalized_path(path)
    df.to_excel(target, index=False)


@dataclass(frozen=True)
class ProjectionMethod:
    column: str
    label: str
    slug: str


PROJECTION_METHODS: List[ProjectionMethod] = [
    ProjectionMethod("moodys_mi_pct_change_2024_2030_employment", "Moody's MI", "moodys_mi"),
    ProjectionMethod("moodys_us_pct_change_2024_2030_employment", "Moody's US", "moodys_us"),
    ProjectionMethod("mi_dtmb_six_year_rate", "DTMB MI", "dtmb_mi"),
    ProjectionMethod("bls_us_six_year_employment_rate_change", "BLS US", "bls_us"),
]

DETAIL_MULTIPLIER_REL_PATH = Path("data") / "interim" / "moodys_mi_annual_multipliers_2024_2034.csv"
DETAIL_PROJECTION_METHOD = ProjectionMethod("", "Moody's MI (detail)", "moodys_mi_detail")
ADDITIONAL_PROJECTION_METHODS: List[ProjectionMethod] = [DETAIL_PROJECTION_METHOD]
ALL_PROJECTION_METHODS: List[ProjectionMethod] = PROJECTION_METHODS + ADDITIONAL_PROJECTION_METHODS


def _major_code_and_name(occcd: str) -> tuple[str, str]:
    if not isinstance(occcd, str):
        prefix = "00"
    else:
        match = re.match(r"^(\d{2})", occcd.strip())
        prefix = match.group(1) if match else "00"
    return MAJOR_OCCUPATIONS.get(
        prefix,
        (f"{prefix}-0000", f"{prefix} Occupations"),
    )


def _weighted_average(values: pd.Series | None, weights: pd.Series | None) -> float:
    if values is None or weights is None:
        return np.nan
    v = pd.to_numeric(values, errors="coerce")
    w = pd.to_numeric(weights, errors="coerce").fillna(0.0)
    mask = (w > 0) & (~v.isna())
    if not mask.any():
        return np.nan
    return float((v[mask] * w[mask]).sum() / w[mask].sum())


def _weighted_mode(values: pd.Series | None, weights: pd.Series | None, default: str = "Unreported") -> str:
    if values is None or weights is None:
        return default
    w = pd.to_numeric(weights, errors="coerce").fillna(0.0)
    df = pd.DataFrame({"value": values, "weight": w})
    df["value"] = df["value"].fillna("").astype(str).str.strip()
    df = df[df["value"] != ""]
    if df.empty:
        return default
    grouped = df.groupby("value", sort=False)["weight"].sum()
    if grouped.empty:
        return default
    max_weight = grouped.max()
    top_values = grouped[grouped == max_weight].index.tolist()
    if not top_values:
        return default
    return sorted(top_values)[0]


def load_base_dataframe(repo_root: Path) -> pd.DataFrame:
    """Load SAM shares and projection rates, returning merged dataframe."""
    sam_path = repo_root / "data" / "intermediate" / "sam_naics_shares_v2" / "sam_auto_naics4_mobility38.csv"
    proj_path = repo_root / "data" / "intermediate" / "employment_projection_comparison.csv"

    sam = pd.read_csv(sam_path, dtype={"naics_code": str})
    proj = pd.read_csv(proj_path, dtype={"naics_code": str})

    sam["naics_code"] = sam["naics_code"].str.strip().str.zfill(4)
    proj["naics_code"] = proj["naics_code"].str.strip().str.zfill(4)

    df = sam.merge(
        proj[
            [
                "naics_code",
                "employment_qcew_2024",
                "moodys_mi_pct_change_2024_2030_employment",
                "moodys_us_pct_change_2024_2030_employment",
                "mi_dtmb_six_year_rate",
                "bls_us_six_year_employment_rate_change",
            ]
        ],
        on="naics_code",
        how="left",
        suffixes=("", "_proj"),
    )

    df.rename(
        columns={
            "employment_qcew_2024": "employment_qcew_base",
            "employment_qcew_2024_proj": "employment_qcew_base_proj",
        },
        inplace=True,
    )
    df["employment_qcew_base"] = (
        df["employment_qcew_base"]
        .fillna(df["employment_qcew_base_proj"])
        .fillna(0.0)
    )
    df.drop(columns=["employment_qcew_base_proj"], inplace=True, errors="ignore")

    base_lookup = load_monthly_base_lookup(repo_root / MONTHLY_QCEW_PATH, BASE_PERIOD)
    if base_lookup:
        df["employment_qcew_base"] = df["naics_code"].map(base_lookup).fillna(df["employment_qcew_base"])

    df["segment_name"] = df["segment_name"].astype(str).str.strip()
    df["segment_subgroup"] = df["segment_name"]
    df["segment_id"] = pd.to_numeric(df["segment_id"], errors="coerce").astype("Int64")
    df["segment_name"] = df["segment_id"].map(SEGMENT_LABELS).fillna(df["segment_name"])

    df["stage"] = df["stage"].astype(str).str.strip()
    df["stage_lower"] = df["stage"].str.lower()
    df["naics_title"] = df["naics_title"].astype(str).str.strip()

    target_mask = (df["stage_lower"].isin(TARGET_STAGE)) | (df["naics_code"].isin(OEM_NAICS))
    share = df["auto_share_of_output"].fillna(0.0).clip(lower=0.0, upper=1.0)
    df["share_applied"] = np.where(target_mask, share, 1.0)

    df["base_employment"] = df["employment_qcew_base"].astype(float)
    df["auto_base_employment"] = df["base_employment"] * df["share_applied"]

    return df


def load_historical_qcew(repo_root: Path, base_df: pd.DataFrame) -> pd.DataFrame:
    """Load historical QCEW (2001-2023) employment for the tracked NAICS codes."""
    hist_path = repo_root / "data" / "raw" / "MI-QCEW-38-NAICS-2001-2024.xlsx"
    if not hist_path.exists():
        return pd.DataFrame()

    raw = pd.read_excel(hist_path, sheet_name="BLS Data Series", skiprows=2)
    if raw.empty:
        return pd.DataFrame()

    header = raw.iloc[0].tolist()
    raw = raw.iloc[1:].copy()
    raw.columns = header
    raw = raw.rename(columns={"Series ID": "series_id"})

    value_cols = [c for c in raw.columns if isinstance(c, str) and c.startswith("Annual")]
    if not value_cols:
        return pd.DataFrame()

    hist = raw.melt(
        id_vars="series_id",
        value_vars=value_cols,
        var_name="year_label",
        value_name="employment_raw",
    )
    hist["year"] = (
        hist["year_label"]
        .astype(str)
        .str.extract(r"(\d{4})")
        .astype(float)
    )
    hist["employment_raw"] = pd.to_numeric(hist["employment_raw"], errors="coerce")
    hist = hist.dropna(subset=["year", "employment_raw"])
    hist["year"] = hist["year"].astype(int)
    hist = hist[hist["year"] < YEARS[0]]
    if hist.empty:
        return hist

    hist["naics_code"] = hist["series_id"].astype(str).str[-4:]
    meta_cols = [
        "naics_code",
        "naics_title",
        "segment_id",
        "segment_name",
        "segment_subgroup",
        "stage",
        "share_applied",
    ]
    meta = base_df[meta_cols].drop_duplicates("naics_code")
    hist = hist.merge(meta, on="naics_code", how="inner")
    if hist.empty:
        return hist

    hist["value_type"] = "QCEW"
    hist["share_applied"] = hist["share_applied"].fillna(1.0)
    hist["employment_auto"] = hist["employment_raw"] * hist["share_applied"]
    hist["projection_rate_total"] = np.nan
    hist["projection_cagr"] = np.nan
    hist.drop(columns=["year_label"], inplace=True)

    return hist


def build_historical_naics_timeseries(repo_root: Path, base_df: pd.DataFrame) -> pd.DataFrame:
    """Attach historical NAICS employment (2001-2023) to each projection method."""
    hist = load_historical_qcew(repo_root, base_df)
    if hist.empty:
        return hist

    frames: list[pd.DataFrame] = []
    for method in PROJECTION_METHODS:
        temp = hist.copy()
        temp["projection_method"] = method.slug
        temp["projection_label"] = method.label
        frames.append(temp)
    return pd.concat(frames, ignore_index=True)


def _compute_multiplier(total_rate: np.ndarray, years_ahead: int) -> np.ndarray:
    """Return growth multiplier given total six-year rate and years ahead."""
    # Handle edge cases where rate <= -1 (industry disappears)
    total_rate = np.nan_to_num(total_rate, nan=0.0)
    invalid = total_rate <= -1.0
    # CAGR for six-year horizon; guard against precision issues for small negatives
    with np.errstate(invalid="ignore"):
        cagr = np.where(
            invalid,
            -1.0,
            np.power(1.0 + total_rate, 1.0 / 6.0) - 1.0,
        )

    if years_ahead == 0:
        mult = np.ones_like(total_rate)
    else:
        mult = np.where(
            cagr <= -1.0,
            0.0,
            np.power(1.0 + cagr, years_ahead),
        )
    mult = np.nan_to_num(mult, nan=1.0, posinf=0.0, neginf=0.0)
    return mult, cagr


def build_naics_timeseries(base_df: pd.DataFrame) -> pd.DataFrame:
    """Construct NAICS time series for all projection methods."""
    records = []

    for method in PROJECTION_METHODS:
        if method.column not in base_df.columns:
            rates = np.zeros(len(base_df), dtype=float)
        else:
            rates = base_df[method.column].fillna(0.0).astype(float).to_numpy()

        for year in YEARS:
            years_ahead = year - YEARS[0]
            multiplier, cagr = _compute_multiplier(rates, years_ahead)

            out = base_df.copy()
            out["projection_method"] = method.slug
            out["projection_label"] = method.label
            out["projection_rate_total"] = rates
            out["projection_cagr"] = np.where(cagr <= -1.0, np.nan, cagr)
            out["year"] = year
            out["value_type"] = "QCEW" if year == YEARS[0] else "Forecast"
            out["employment_auto"] = out["auto_base_employment"] * multiplier
            out["employment_raw"] = out["base_employment"] * multiplier
            out["employment_auto"] = out["employment_auto"].astype(float)
            out["employment_raw"] = out["employment_raw"].astype(float)
            records.append(out)

    if not records:
        return pd.DataFrame()

    naics_ts = pd.concat(records, ignore_index=True)
    numeric_cols = ["employment_auto", "employment_raw", "projection_rate_total", "projection_cagr"]
    naics_ts[numeric_cols] = naics_ts[numeric_cols].apply(pd.to_numeric, errors="coerce")
    return naics_ts


def load_moodys_detail_multipliers(repo_root: Path) -> pd.DataFrame:
    """Load detailed Moody's MI year-over-year multipliers if available."""
    path = repo_root / DETAIL_MULTIPLIER_REL_PATH
    if not path.exists():
        return pd.DataFrame()

    df = pd.read_csv(path, dtype={"naics_code": str})
    df["naics_code"] = df["naics_code"].astype(str).str.strip().str.zfill(4)
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df = df.dropna(subset=["year"])
    df["year"] = df["year"].astype(int)
    df["yoy_multiplier"] = pd.to_numeric(df["yoy_multiplier"], errors="coerce")
    df["yoy_multiplier"] = df["yoy_multiplier"].replace([np.inf, -np.inf], np.nan).fillna(1.0)
    return df


def build_moodys_detail_timeseries(base_df: pd.DataFrame, multipliers: pd.DataFrame) -> pd.DataFrame:
    """Create NAICS time series using Moody's MI detailed growth path."""
    if multipliers.empty:
        return pd.DataFrame()

    forecast_years = [year for year in YEARS if year > YEARS[0]]
    if not forecast_years:
        return pd.DataFrame()

    meta_cols = [
        "naics_code",
        "naics_title",
        "segment_id",
        "segment_name",
        "segment_subgroup",
        "stage",
        "share_applied",
        "auto_base_employment",
        "base_employment",
    ]
    base_meta = base_df[meta_cols].copy()
    base_meta["naics_code"] = base_meta["naics_code"].astype(str).str.strip().str.zfill(4)

    idx = pd.MultiIndex.from_product(
        [base_meta["naics_code"].unique(), forecast_years], names=["naics_code", "year"]
    )
    yoy = multipliers[multipliers["year"].isin(forecast_years)].copy()
    yoy = yoy.set_index(["naics_code", "year"])
    yoy = yoy.reindex(idx)
    yoy = yoy.reset_index()
    yoy["yoy_multiplier"] = pd.to_numeric(yoy["yoy_multiplier"], errors="coerce")
    yoy["yoy_multiplier"] = yoy["yoy_multiplier"].replace([np.inf, -np.inf], np.nan).fillna(1.0)
    yoy.sort_values(["naics_code", "year"], inplace=True)
    yoy["cumulative_multiplier"] = yoy.groupby("naics_code")["yoy_multiplier"].cumprod()

    forecast = yoy.merge(base_meta, on="naics_code", how="left")
    forecast["projection_method"] = DETAIL_PROJECTION_METHOD.slug
    forecast["projection_label"] = DETAIL_PROJECTION_METHOD.label
    forecast["projection_rate_total"] = np.nan
    forecast["projection_cagr"] = np.nan
    forecast["value_type"] = "Forecast"
    forecast["employment_auto"] = forecast["auto_base_employment"] * forecast["cumulative_multiplier"]
    forecast["employment_raw"] = forecast["base_employment"] * forecast["cumulative_multiplier"]
    forecast["year"] = forecast["year"].astype(int)

    base_rows = base_meta.copy()
    base_rows["projection_method"] = DETAIL_PROJECTION_METHOD.slug
    base_rows["projection_label"] = DETAIL_PROJECTION_METHOD.label
    base_rows["projection_rate_total"] = np.nan
    base_rows["projection_cagr"] = np.nan
    base_rows["year"] = YEARS[0]
    base_rows["value_type"] = "QCEW"
    base_rows["employment_auto"] = base_rows["auto_base_employment"]
    base_rows["employment_raw"] = base_rows["base_employment"]

    detail = pd.concat([base_rows, forecast], ignore_index=True, sort=False)
    cols = [
        "projection_method",
        "projection_label",
        "naics_code",
        "naics_title",
        "segment_id",
        "segment_name",
        "segment_subgroup",
        "stage",
        "year",
        "value_type",
        "share_applied",
        "employment_auto",
        "employment_raw",
        "projection_rate_total",
        "projection_cagr",
    ]
    detail = detail[cols]
    detail["employment_auto"] = pd.to_numeric(detail["employment_auto"], errors="coerce")
    detail["employment_raw"] = pd.to_numeric(detail["employment_raw"], errors="coerce")
    return detail


def aggregate_segments(naics_ts: pd.DataFrame) -> pd.DataFrame:
    group_cols = [
        "projection_method",
        "projection_label",
        "year",
        "value_type",
        "segment_id",
    ]
    agg = (
        naics_ts.groupby(group_cols, as_index=False)
        .agg(
            employment_auto=("employment_auto", "sum"),
            employment_raw=("employment_raw", "sum"),
        )
    )
    agg["segment_name"] = agg["segment_id"].map(SEGMENT_LABELS)
    agg["auto_share_ratio"] = np.where(
        agg["employment_raw"] > 0,
        agg["employment_auto"] / agg["employment_raw"],
        np.nan,
    )
    return agg


def aggregate_stages(naics_ts: pd.DataFrame) -> pd.DataFrame:
    group_cols = [
        "projection_method",
        "projection_label",
        "year",
        "value_type",
        "stage",
    ]
    agg = (
        naics_ts.groupby(group_cols, as_index=False)
        .agg(
            employment_auto=("employment_auto", "sum"),
            employment_raw=("employment_raw", "sum"),
        )
    )
    agg["auto_share_ratio"] = np.where(
        agg["employment_raw"] > 0,
        agg["employment_auto"] / agg["employment_raw"],
        np.nan,
    )
    # Add combined upstream+core view (core captured by OEM stage)
    uc_mask = naics_ts["stage"].str.lower().isin({"upstream", "oem"})
    uc = (
        naics_ts.loc[uc_mask]
        .groupby(["projection_method", "projection_label", "year", "value_type"], as_index=False)
        .agg(
            employment_auto=("employment_auto", "sum"),
            employment_raw=("employment_raw", "sum"),
        )
    )
    uc["stage"] = UPSTREAM_CORE_STAGE_LABEL
    uc["auto_share_ratio"] = np.where(
        uc["employment_raw"] > 0,
        uc["employment_auto"] / uc["employment_raw"],
        np.nan,
    )
    return pd.concat([agg, uc], ignore_index=True)


def build_upstream_core_segment(naics_ts: pd.DataFrame) -> pd.DataFrame:
    """Create aggregate segment representing Upstream + Core/OEM."""
    if naics_ts.empty:
        return pd.DataFrame()
    stage_mask = naics_ts["stage"].astype(str).str.lower().isin(UPSTREAM_CORE_STAGES)
    uc = (
        naics_ts.loc[stage_mask]
        .groupby(["projection_method", "projection_label", "year", "value_type"], as_index=False)
        .agg(
            employment_auto=("employment_auto", "sum"),
            employment_raw=("employment_raw", "sum"),
        )
    )
    if uc.empty:
        return uc
    uc["segment_id"] = UPSTREAM_CORE_SEGMENT_ID
    uc["segment_name"] = UPSTREAM_CORE_SEGMENT_NAME
    uc["auto_share_ratio"] = np.where(
        uc["employment_raw"] > 0,
        uc["employment_auto"] / uc["employment_raw"],
        np.nan,
    )
    return uc[
        [
            "projection_method",
            "projection_label",
            "year",
            "value_type",
            "segment_id",
            "segment_name",
            "employment_auto",
            "employment_raw",
            "auto_share_ratio",
        ]
    ]


def write_outputs(
    output_dir: Path,
    naics_ts: pd.DataFrame,
    segment_summary: pd.DataFrame,
    stage_summary: pd.DataFrame,
) -> None:
    naics_path = output_dir / "sam_employment_naics_timeseries.csv"
    segment_path = output_dir / "sam_employment_segment_timeseries.csv"
    stage_path = output_dir / "sam_employment_stage_timeseries.csv"

    naics_cols = [
        "projection_method",
        "projection_label",
        "naics_code",
        "naics_title",
        "segment_id",
        "segment_name",
        "segment_subgroup",
        "stage",
        "year",
        "value_type",
        "share_applied",
        "employment_auto",
        "employment_raw",
        "projection_rate_total",
        "projection_cagr",
    ]
    write_csv(naics_ts[naics_cols], naics_path)

    segment_ts = segment_summary.copy()
    segment_ts["adjustment_source"] = ADJUSTMENT_SOURCE
    segment_ts["forecast_source"] = segment_ts["projection_method"]
    segment_ts_cols = [
        "adjustment_source",
        "forecast_source",
        "projection_label",
        "segment_id",
        "segment_name",
        "year",
        "value_type",
        "employment_auto",
        "employment_raw",
        "auto_share_ratio",
    ]
    write_csv(segment_ts[segment_ts_cols], segment_path)

    stage_ts = stage_summary.copy()
    stage_ts["adjustment_source"] = ADJUSTMENT_SOURCE
    stage_ts["forecast_source"] = stage_ts["projection_method"]
    stage_cols = [
        "adjustment_source",
        "forecast_source",
        "projection_label",
        "stage",
        "year",
        "value_type",
        "employment_auto",
        "employment_raw",
        "auto_share_ratio",
    ]
    write_csv(stage_ts[stage_cols], stage_path)

    # Prepare segment totals file for potential downstream use
    segment_for_occ = segment_ts.rename(columns={"employment_auto": "employment_qcew"})
    occ_cols = [
        "segment_id",
        "segment_name",
        "year",
        "adjustment_source",
        "forecast_source",
        "value_type",
        "employment_qcew",
    ]
    occ_path = output_dir / "sam_segment_totals_for_occ.csv"
    write_csv(segment_for_occ[occ_cols], occ_path)


def load_mcda_shares(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "occ_level" in df.columns:
        df = df[df["occ_level"].astype(str).str.lower() == "detailed"].copy()
    if "segment" not in df.columns:
        raise ValueError("MCDA staffing file must include a 'segment' column.")

    df["segment_id"] = (
        df["segment"]
        .astype(str)
        .str.extract(r"^(\d+)")
        .astype(float)
        .astype("Int64")
    )
    df["segment_name"] = df["segment"].astype(str).str.strip()
    df["occcd"] = df["occcd"].astype(str).str.strip()
    df["soctitle"] = df["soctitle"].astype(str).str.strip()
    df["share_2024"] = pd.to_numeric(df.get("pct_seg_detailed_2024"), errors="coerce").fillna(0.0)
    df["ep_openings_annual_avg"] = pd.to_numeric(df.get("ep_openings_annual_avg"), errors="coerce").fillna(0.0)
    df["ep_employment_2024"] = pd.to_numeric(df.get("ep_employment_2024"), errors="coerce").fillna(0.0)
    df["ep_employment_2034"] = pd.to_numeric(df.get("ep_employment_2034"), errors="coerce").fillna(0.0)
    avg_ep_emp = (df["ep_employment_2024"] + df["ep_employment_2034"]) / 2.0
    df["ep_openings_ratio"] = np.where(avg_ep_emp > 0, df["ep_openings_annual_avg"] / avg_ep_emp, 0.0)
    df["empl_2021"] = pd.to_numeric(df.get("empl_2021"), errors="coerce")
    df["ep_entry_education"] = df.get("ep_entry_education", np.nan)
    df["ep_work_experience"] = df.get("ep_work_experience", np.nan)
    df["ep_on_the_job_training"] = df.get("ep_on_the_job_training", np.nan)
    df["ep_edu_grouped"] = df.get("ep_edu_grouped", np.nan)
    salary_series = df.get("ep_avg_annual_salary")
    if salary_series is None:
        salary_series = df.get("ep_median_annual_wage_2024")
    if salary_series is None:
        df["ep_avg_annual_salary"] = np.nan
    else:
        df["ep_avg_annual_salary"] = pd.to_numeric(salary_series, errors="coerce")
    df = df.dropna(subset=["segment_id"])
    return df[
        [
            "segment_id",
            "segment_name",
            "occcd",
            "soctitle",
            "share_2024",
            "ep_entry_education",
            "ep_work_experience",
            "ep_on_the_job_training",
            "ep_edu_grouped",
            "ep_avg_annual_salary",
            "ep_openings_annual_avg",
            "ep_employment_2024",
            "ep_employment_2034",
            "ep_openings_ratio",
            "empl_2021",
        ]
    ]


def load_bls_shares(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["segment_id"] = pd.to_numeric(df["segment_id"], errors="coerce").astype("Int64")
    df = df.dropna(subset=["segment_id"])
    df["segment_id"] = df["segment_id"].astype(int)
    df["occcd"] = df["Occupation Code"].astype(str).str.strip()
    df["share_2024_bls"] = pd.to_numeric(df["segment_share_2024"], errors="coerce")
    df["share_2034_bls"] = pd.to_numeric(df["segment_share_2034"], errors="coerce")
    return df[["segment_id", "occcd", "share_2024_bls", "share_2034_bls"]]


def build_occupation_outputs(
    segment_summary: pd.DataFrame,
    mcda_df: pd.DataFrame,
    bls_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Create occupation-level employment series using BLS drift-adjusted shares."""
    seg_key = ["projection_method", "projection_label", "segment_id", "segment_name", "year"]
    seg_map = (
        segment_summary[seg_key + ["employment_auto"]]
        .set_index(["projection_method", "segment_id", "year"])
        ["employment_auto"]
        .to_dict()
    )
    raw_map = (
        segment_summary[seg_key + ["employment_raw"]]
        .set_index(["projection_method", "segment_id", "year"])
        ["employment_raw"]
        .to_dict()
    )
    total_map = (
        segment_summary.groupby(["projection_method", "year"])["employment_auto"]
        .sum()
        .to_dict()
    )

    segment_name_lookup = (
        segment_summary[["segment_id", "segment_name"]]
        .drop_duplicates()
        .set_index("segment_id")["segment_name"]
        .to_dict()
    )

    available_methods = set(segment_summary["projection_method"].unique())

    shares = mcda_df.merge(bls_df, on=["segment_id", "occcd"], how="left")
    shares["share_2024_bls"] = pd.to_numeric(shares["share_2024_bls"], errors="coerce")
    shares["share_2034_bls"] = pd.to_numeric(shares["share_2034_bls"], errors="coerce")
    shares["share_2024_bls"] = shares["share_2024_bls"].fillna(shares["share_2024"])
    shares["share_2034_bls"] = shares["share_2034_bls"].fillna(shares["share_2024_bls"])

    years_span = max(YEARS[-1] - YEARS[0], 1)
    shares["growth_factor"] = 1.0
    valid_mask = shares["share_2024_bls"] > 0
    shares.loc[valid_mask, "growth_factor"] = (
        shares.loc[valid_mask, "share_2034_bls"] / shares.loc[valid_mask, "share_2024_bls"]
    ) ** (1.0 / years_span)
    shares["growth_factor"] = shares["growth_factor"].replace([np.inf, -np.inf], 1.0).fillna(1.0)

    share_frames: list[pd.DataFrame] = []
    for year in YEARS:
        power = min(max(year - YEARS[0], 0), years_span)
        temp = shares.copy()
        temp["share_unscaled"] = temp["share_2024"] * np.power(temp["growth_factor"], power)
        totals = temp.groupby("segment_id")["share_unscaled"].transform("sum")
        temp["share"] = np.where(totals > 0, temp["share_unscaled"] / totals, 0.0)
        temp["share"] = temp["share"].replace([np.inf, -np.inf], np.nan).fillna(temp["share_2024"])
        temp["year"] = year
        temp["share_2034"] = temp["share_2034_bls"]
        share_frames.append(
            temp[
                [
                    "segment_id",
                    "segment_name",
                    "occcd",
                    "soctitle",
                    "year",
                    "share",
                    "share_2024",
                    "share_2034",
                    "ep_entry_education",
                    "ep_work_experience",
                    "ep_on_the_job_training",
                    "ep_edu_grouped",
                    "ep_avg_annual_salary",
                    "ep_openings_annual_avg",
                    "ep_employment_2024",
                    "ep_employment_2034",
                    "ep_openings_ratio",
                    "empl_2021",
                ]
            ]
        )

    if not share_frames:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    shares_long = pd.concat(share_frames, ignore_index=True)
    shares_long["ep_edu_training_grouped"] = shares_long.apply(
        lambda row: derive_training_group(row["ep_edu_grouped"], row["ep_on_the_job_training"]),
        axis=1,
    )
    share_lookup = (
        shares_long.set_index(["segment_id", "occcd", "year"])["share"].to_dict()
    )
    share2034_lookup = (
        shares_long[shares_long["year"] == YEARS[-1]]
        .set_index(["segment_id", "occcd"])["share_2034"]
        .to_dict()
    )

    records: list[dict[str, object]] = []
    for method in ALL_PROJECTION_METHODS:
        if method.slug not in available_methods:
            continue
        base_totals = segment_summary[
            (segment_summary["projection_method"] == method.slug) & (segment_summary["year"] == YEARS[0])
        ]
        base_auto_lookup = base_totals.set_index("segment_id")["employment_auto"].to_dict()
        base_raw_lookup = base_totals.set_index("segment_id")["employment_raw"].to_dict()

        base_occ = shares_long[shares_long["year"] == YEARS[0]].copy()

        for _, occ in base_occ.iterrows():
            seg_id = int(occ["segment_id"])
            if seg_id not in base_auto_lookup:
                continue

            share_base = float(occ["share"])
            if share_base <= 0:
                continue

            base_segment_emp_auto = base_auto_lookup.get(seg_id, 0.0)
            ratio_openings = float(occ.get("ep_openings_ratio", 0.0))

            for year in YEARS:
                key = (method.slug, seg_id, year)
                seg_emp_auto = seg_map.get(key)
                if seg_emp_auto is None or np.isnan(seg_emp_auto):
                    continue
                seg_emp_raw = raw_map.get(key, 0.0)

                share = share_lookup.get((seg_id, occ["occcd"], year), share_base)
                employment_auto = share * seg_emp_auto
                employment_raw = share * seg_emp_raw
                employment = employment_auto  # retain legacy column for compatibility
                openings = ratio_openings * employment_auto

                records.append(
                    {
                        "segment_id": seg_id,
                        "segment_name": segment_name_lookup.get(seg_id, occ["segment_name"]),
                        "year": year,
                        "methodology": f"{ADJUSTMENT_SOURCE}_{method.slug}",
                        "projection_method": method.slug,
                        "projection_label": method.label,
                        "occcd": occ["occcd"],
                        "soctitle": occ["soctitle"],
                        "employment": employment,
                        "employment_auto": employment_auto,
                        "employment_raw": employment_raw,
                        "share": share,
                        "share_2024": share_base,
                        "share_2034": share2034_lookup.get((seg_id, occ["occcd"]), share_base),
                        "ep_entry_education": occ["ep_entry_education"],
                        "ep_work_experience": occ["ep_work_experience"],
                        "ep_on_the_job_training": occ["ep_on_the_job_training"],
                        "ep_edu_grouped": occ["ep_edu_grouped"],
                        "ep_edu_training_grouped": occ["ep_edu_training_grouped"],
                        "ep_avg_annual_salary": occ["ep_avg_annual_salary"],
                        "ep_employment_2024": occ.get("ep_employment_2024", np.nan),
                        "ep_employment_2034": occ.get("ep_employment_2034", np.nan),
                        "ep_openings_ratio": ratio_openings,
                        "empl_2021": occ["empl_2021"],
                        "ep_openings_annual_avg": occ["ep_openings_annual_avg"],
                        "openings": openings,
                    }
                )

    occ_df = pd.DataFrame.from_records(records)
    if occ_df.empty:
        return occ_df, occ_df.copy(), occ_df.copy()

    group_cols = [
        "methodology",
        "projection_method",
        "projection_label",
        "occcd",
        "soctitle",
        "ep_entry_education",
        "ep_work_experience",
        "ep_on_the_job_training",
        "ep_edu_grouped",
        "ep_edu_training_grouped",
        "ep_avg_annual_salary",
        "year",
    ]
    agg = (
        occ_df.groupby(group_cols, as_index=False, dropna=False)
        .agg(
            employment=("employment", "sum"),
            employment_auto=("employment_auto", "sum"),
            employment_raw=("employment_raw", "sum"),
            openings=("openings", "sum"),
            ep_openings_annual_avg=("ep_openings_annual_avg", "sum"),
            empl_2021=("empl_2021", "sum"),
        )
    )

    def _total_share(row: pd.Series) -> float:
        total = total_map.get((row["projection_method"], row["year"]), 0.0)
        if total > 0:
            return row["employment"] / total
        return np.nan

    agg["share"] = agg.apply(_total_share, axis=1)
    agg["share_2024"] = agg.apply(lambda r: _total_share(r) if r["year"] == YEARS[0] else np.nan, axis=1)
    agg["share_2034"] = agg.apply(lambda r: _total_share(r) if r["year"] == YEARS[-1] else np.nan, axis=1)

    agg["segment_id"] = 0
    agg["segment_name"] = "0. All Segments"

    agg["share_2024"] = agg.groupby(
        ["methodology", "projection_method", "occcd"]
    )["share_2024"].transform("max")
    agg["share_2034"] = agg.groupby(
        ["methodology", "projection_method", "occcd"]
    )["share_2034"].transform("max")

    combined = pd.concat([occ_df, agg], ignore_index=True)
    combined.sort_values(["methodology", "occcd", "year"], inplace=True)

    occ_2030 = combined[combined["year"] == 2030].copy()
    base_year = YEARS[0]
    base_cols = [
        "methodology",
        "projection_method",
        "projection_label",
        "segment_id",
        "segment_name",
        "occcd",
        "employment_auto",
        "employment_raw",
    ]
    base_lookup = (
        combined[combined["year"] == base_year][base_cols]
        .rename(
            columns={
                "employment_auto": "employment_auto_2024",
                "employment_raw": "employment_raw_2024",
            }
        )
    )
    occ_2030 = occ_2030.merge(
        base_lookup,
        on=[
            "methodology",
            "projection_method",
            "projection_label",
            "segment_id",
            "segment_name",
            "occcd",
        ],
        how="left",
    )
    occ_2030["employment_auto_change"] = occ_2030["employment_auto"] - occ_2030["employment_auto_2024"]
    occ_2030["employment_raw_change"] = occ_2030["employment_raw"] - occ_2030["employment_raw_2024"]
    occ_2030["employment_auto_pct_change"] = np.where(
        occ_2030["employment_auto_2024"] != 0,
        occ_2030["employment_auto_change"] / occ_2030["employment_auto_2024"],
        np.nan,
    )
    occ_2030["employment_raw_pct_change"] = np.where(
        occ_2030["employment_raw_2024"] != 0,
        occ_2030["employment_raw_change"] / occ_2030["employment_raw_2024"],
        np.nan,
    )

    validation = (
        combined[combined["segment_id"] != 0]
        .groupby(["projection_method", "segment_id", "segment_name", "year"], as_index=False)["employment"]
        .sum()
        .merge(
            segment_summary[["projection_method", "segment_id", "segment_name", "year", "employment_auto"]],
            on=["projection_method", "segment_id", "segment_name", "year"],
            how="left",
        )
    )
    validation["difference"] = validation["employment"] - validation["employment_auto"]
    return combined, occ_2030, validation


def aggregate_stage_occ(
    occ_2030: pd.DataFrame,
    stage_summary: pd.DataFrame,
    segment_stage_lookup: dict[int, str],
) -> pd.DataFrame:
    """Aggregate 2030 occupation totals to stages (Upstream, OEM, Downstream, Upstream+Core)."""
    stage_map = (
        stage_summary[["stage", "year", "projection_method", "projection_label"]]
        .drop_duplicates()
        .set_index(["projection_method", "stage"])["projection_label"]
    )
    mapping = {
        "Upstream": "Upstream",
        "OEM": "Core/OEM",
        "Downstream": "Downstream",
        "Upstream+Core": "Upstream + Core/OEM",
    }
    stage_df = stage_summary[stage_summary["year"] == 2030].copy()
    stage_df["stage_clean"] = stage_df["stage"].map(mapping).fillna(stage_df["stage"])

    occ = occ_2030[occ_2030["segment_id"] != 0].copy()
    occ["stage"] = occ["segment_id"].map(segment_stage_lookup)
    occ = occ[occ["stage"].notna()].copy()
    meta_cols = [
        "ep_entry_education",
        "ep_work_experience",
        "ep_on_the_job_training",
        "ep_edu_grouped",
        "ep_edu_training_grouped",
    ]
    for col in meta_cols:
        occ[col] = occ[col].fillna("Unreported").replace("", "Unreported")
    occ["ep_avg_annual_salary"] = pd.to_numeric(occ.get("ep_avg_annual_salary"), errors="coerce")
    occ["stage_clean"] = occ["stage"].map(mapping).fillna(occ["stage"])
    uc_rows = occ[occ["stage_clean"].isin({"Upstream", "Core/OEM"})].copy()
    uc_rows["stage_clean"] = "Upstream + Core/OEM"
    occ_aug = pd.concat([occ, uc_rows], ignore_index=True)

    agg_cols = [
        "stage_clean",
        "methodology",
        "projection_method",
        "projection_label",
        "occcd",
        "soctitle",
        "ep_entry_education",
        "ep_work_experience",
        "ep_on_the_job_training",
        "ep_edu_grouped",
        "ep_edu_training_grouped",
        "ep_avg_annual_salary",
    ]
    grouped = (
        occ_aug.groupby(agg_cols, dropna=False)[
            [
                "employment",
                "employment_auto",
                "employment_raw",
                "employment_auto_2024",
                "employment_raw_2024",
                "employment_auto_change",
                "employment_raw_change",
                "openings",
                "ep_openings_annual_avg",
                "empl_2021",
            ]
        ]
        .sum()
        .reset_index()
    )
    grouped["employment_auto_pct_change"] = np.where(
        grouped["employment_auto_2024"] != 0,
        grouped["employment_auto_change"] / grouped["employment_auto_2024"],
        np.nan,
    )
    grouped["employment_raw_pct_change"] = np.where(
        grouped["employment_raw_2024"] != 0,
        grouped["employment_raw_change"] / grouped["employment_raw_2024"],
        np.nan,
    )
    grouped["year"] = 2030
    return grouped


SEGMENT_SUM_COLUMNS = [
    "employment",
    "employment_auto",
    "employment_raw",
    "employment_auto_2024",
    "employment_raw_2024",
    "employment_auto_change",
    "employment_raw_change",
    "openings",
    "ep_openings_annual_avg",
    "empl_2021",
]

STAGE_SUM_COLUMNS = SEGMENT_SUM_COLUMNS.copy()


def _aggregate_major_rows(
    df: pd.DataFrame,
    group_cols: list[str],
    sum_cols: list[str],
    include_share: bool,
) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    records: list[dict[str, object]] = []
    for keys, group in df.groupby(group_cols, dropna=False, sort=False):
        record = {col: key for col, key in zip(group_cols, keys)}
        weight_current = pd.to_numeric(group.get("employment_auto"), errors="coerce").fillna(0.0).clip(lower=0.0)
        weight_base = pd.to_numeric(group.get("employment_auto_2024"), errors="coerce").fillna(0.0).clip(lower=0.0)
        for col in sum_cols:
            if col in group.columns:
                record[col] = group[col].sum()
        record["ep_avg_annual_salary"] = _weighted_average(group.get("ep_avg_annual_salary"), weight_current)
        for meta in [
            "ep_entry_education",
            "ep_work_experience",
            "ep_on_the_job_training",
            "ep_edu_grouped",
        ]:
            if meta in group.columns:
                record[meta] = _weighted_mode(group[meta], weight_current)
        if include_share and "share_2034" in group.columns:
            record["share_2034"] = _weighted_average(group.get("share_2034"), weight_base)
        records.append(record)

    return pd.DataFrame.from_records(records)


def _compute_group_share(df: pd.DataFrame, group_cols: list[str], value_col: str) -> pd.Series:
    totals = df.groupby(group_cols)[value_col].transform("sum")
    return np.where(totals > 0, df[value_col] / totals, np.nan)


def _finalize_segment_major(df: pd.DataFrame, base_cols: list[str]) -> pd.DataFrame:
    if df.empty:
        return df

    df["employment_auto_change"] = df["employment_auto"] - df["employment_auto_2024"]
    df["employment_raw_change"] = df["employment_raw"] - df["employment_raw_2024"]
    df["employment_auto_pct_change"] = np.where(
        df["employment_auto_2024"] != 0,
        df["employment_auto_change"] / df["employment_auto_2024"],
        np.nan,
    )
    df["employment_raw_pct_change"] = np.where(
        df["employment_raw_2024"] != 0,
        df["employment_raw_change"] / df["employment_raw_2024"],
        np.nan,
    )
    df["share"] = _compute_group_share(df, base_cols, "employment_auto")
    df["share_2024"] = _compute_group_share(df, base_cols, "employment_auto_2024")
    df.sort_values(base_cols + ["occcd"], inplace=True)
    columns = [
        "segment_id",
        "segment_name",
        "year",
        "methodology",
        "projection_method",
        "projection_label",
        "occcd",
        "soctitle",
        "employment",
        "employment_auto",
        "employment_raw",
        "share",
        "share_2024",
        "share_2034",
        "ep_entry_education",
        "ep_work_experience",
        "ep_on_the_job_training",
        "ep_edu_grouped",
        "ep_avg_annual_salary",
        "empl_2021",
        "ep_openings_annual_avg",
        "openings",
        "employment_auto_2024",
        "employment_raw_2024",
        "employment_auto_change",
        "employment_raw_change",
        "employment_auto_pct_change",
        "employment_raw_pct_change",
    ]
    return df[columns]


def _finalize_stage_major(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    df["employment_auto_change"] = df["employment_auto"] - df["employment_auto_2024"]
    df["employment_raw_change"] = df["employment_raw"] - df["employment_raw_2024"]
    df["employment_auto_pct_change"] = np.where(
        df["employment_auto_2024"] != 0,
        df["employment_auto_change"] / df["employment_auto_2024"],
        np.nan,
    )
    df["employment_raw_pct_change"] = np.where(
        df["employment_raw_2024"] != 0,
        df["employment_raw_change"] / df["employment_raw_2024"],
        np.nan,
    )
    df.sort_values([
        "stage_clean",
        "methodology",
        "projection_method",
        "occcd",
    ], inplace=True)
    columns = [
        "stage_clean",
        "methodology",
        "projection_method",
        "projection_label",
        "occcd",
        "soctitle",
        "ep_entry_education",
        "ep_work_experience",
        "ep_on_the_job_training",
        "ep_edu_grouped",
        "ep_avg_annual_salary",
        "employment",
        "employment_auto",
        "employment_raw",
        "employment_auto_2024",
        "employment_raw_2024",
        "employment_auto_change",
        "employment_raw_change",
        "openings",
        "ep_openings_annual_avg",
        "empl_2021",
        "employment_auto_pct_change",
        "employment_raw_pct_change",
        "year",
    ]
    return df[columns]


def build_major_segment_snapshot(segment_df: pd.DataFrame) -> pd.DataFrame:
    if segment_df.empty:
        return pd.DataFrame()

    df = segment_df.copy()
    major_pairs = df["occcd"].apply(_major_code_and_name)
    major_info = pd.DataFrame(major_pairs.tolist(), columns=["major_code", "major_name"], index=df.index)
    df = df.join(major_info)
    base_cols = [
        "segment_id",
        "segment_name",
        "year",
        "methodology",
        "projection_method",
        "projection_label",
    ]
    group_cols = base_cols + ["major_code", "major_name"]
    major = _aggregate_major_rows(df, group_cols, SEGMENT_SUM_COLUMNS, include_share=True)

    total_code, total_name = MAJOR_OCCUPATIONS["00"]
    all_df = df.copy()
    all_df["major_code"] = total_code
    all_df["major_name"] = total_name
    all_major = _aggregate_major_rows(all_df, group_cols, SEGMENT_SUM_COLUMNS, include_share=True)

    combined = pd.concat([major, all_major], ignore_index=True)
    combined.rename(columns={"major_code": "occcd", "major_name": "soctitle"}, inplace=True)
    return _finalize_segment_major(combined, base_cols)


def build_major_stage_snapshot(stage_df: pd.DataFrame) -> pd.DataFrame:
    if stage_df.empty:
        return pd.DataFrame()

    df = stage_df.copy()
    major_pairs = df["occcd"].apply(_major_code_and_name)
    major_info = pd.DataFrame(major_pairs.tolist(), columns=["major_code", "major_name"], index=df.index)
    df = df.join(major_info)
    base_cols = [
        "stage_clean",
        "methodology",
        "projection_method",
        "projection_label",
        "year",
    ]
    group_cols = base_cols + ["major_code", "major_name"]
    major = _aggregate_major_rows(df, group_cols, STAGE_SUM_COLUMNS, include_share=False)

    total_code, total_name = MAJOR_OCCUPATIONS["00"]
    all_df = df.copy()
    all_df["major_code"] = total_code
    all_df["major_name"] = total_name
    all_major = _aggregate_major_rows(all_df, group_cols, STAGE_SUM_COLUMNS, include_share=False)

    combined = pd.concat([major, all_major], ignore_index=True)
    combined.rename(columns={"major_code": "occcd", "major_name": "soctitle"}, inplace=True)
    return _finalize_stage_major(combined)

def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    output_dir = repo_root / "data" / "processed" / "sam_auto_dashboard_2024_refresh"
    output_dir.mkdir(parents=True, exist_ok=True)

    base_df = load_base_dataframe(repo_root)
    detail_multipliers = load_moodys_detail_multipliers(repo_root)
    segment_stage_lookup = (
        base_df[["segment_id", "stage"]]
        .dropna(subset=["segment_id", "stage"])
        .drop_duplicates("segment_id")
        .set_index("segment_id")["stage"]
        .to_dict()
    )
    hist_ts = build_historical_naics_timeseries(repo_root, base_df)
    forecast_components = []
    base_forecast = build_naics_timeseries(base_df)
    if not base_forecast.empty:
        forecast_components.append(base_forecast)
    detail_ts = build_moodys_detail_timeseries(base_df, detail_multipliers)
    if not detail_ts.empty:
        forecast_components.append(detail_ts)
    if forecast_components:
        forecast_ts = pd.concat(forecast_components, ignore_index=True, sort=False)
    else:
        forecast_ts = pd.DataFrame()
    if hist_ts.empty and forecast_ts.empty:
        naics_ts = pd.DataFrame()
    elif hist_ts.empty:
        naics_ts = forecast_ts
    elif forecast_ts.empty:
        naics_ts = hist_ts
    else:
        naics_ts = pd.concat([hist_ts, forecast_ts], ignore_index=True, sort=False)

    if not naics_ts.empty:
        naics_ts.sort_values(
            ["projection_method", "year", "naics_code"],
            inplace=True,
        )
        naics_ts.reset_index(drop=True, inplace=True)

    segment_summary = aggregate_segments(naics_ts)
    stage_summary = aggregate_stages(naics_ts)
    uc_segment = build_upstream_core_segment(naics_ts)
    segment_for_outputs = pd.concat([segment_summary, uc_segment], ignore_index=True, sort=False)

    write_outputs(output_dir, naics_ts, segment_for_outputs, stage_summary)
    segment_change, stage_change = build_segment_change_tables(segment_summary)
    segment_change_path = output_dir / "segment_change_2024_2030.csv"
    stage_change_path = output_dir / "stage_change_2024_2030.csv"
    if not segment_change.empty:
        write_csv(segment_change, segment_change_path)
    if not stage_change.empty:
        write_csv(stage_change, stage_change_path)

    mcda_path = repo_root / "data" / "processed" / "mcda_staffing_detailed_2021_2024.csv"
    mcda_shares = load_mcda_shares(mcda_path)
    bls_path = repo_root / BLS_SEGMENT_SUMMARY
    bls_shares = load_bls_shares(bls_path)
    occ_df, occ_2030, occ_validation = build_occupation_outputs(segment_summary, mcda_shares, bls_shares)

    occ_full_path = output_dir / "sam_occ_segment_totals_2024_2034.csv"
    write_csv(occ_df, occ_full_path)
    occ_2030_path = output_dir / "sam_occ_segment_totals_2030.csv"
    occ_2030_xlsx = output_dir / "sam_occ_segment_totals_2030.xlsx"
    write_csv(occ_2030, occ_2030_path)
    write_excel(occ_2030, occ_2030_xlsx)
    stage_occ_2030 = aggregate_stage_occ(occ_2030, stage_summary, segment_stage_lookup)
    stage_occ_path = output_dir / "sam_occ_stage_totals_2030.csv"
    stage_occ_xlsx = output_dir / "sam_occ_stage_totals_2030.xlsx"
    write_csv(stage_occ_2030, stage_occ_path)
    write_excel(stage_occ_2030, stage_occ_xlsx)
    segment_major = build_major_segment_snapshot(occ_2030)
    if not segment_major.empty:
        segment_major_path = output_dir / "sam_occ_segment_major_totals_2030.csv"
        segment_major_xlsx = output_dir / "sam_occ_segment_major_totals_2030.xlsx"
        write_csv(segment_major, segment_major_path)
        write_excel(segment_major, segment_major_xlsx)
    stage_major = build_major_stage_snapshot(stage_occ_2030)
    if not stage_major.empty:
        stage_major_path = output_dir / "sam_occ_stage_major_totals_2030.csv"
        stage_major_xlsx = output_dir / "sam_occ_stage_major_totals_2030.xlsx"
        write_csv(stage_major, stage_major_path)
        write_excel(stage_major, stage_major_xlsx)
    occ_val_path = output_dir / "sam_occ_segment_totals_validation.csv"
    write_csv(occ_validation, occ_val_path)

    print("SAM-standard dashboard data created:")
    print(f"  NAICS time series -> {output_dir / 'sam_employment_naics_timeseries.csv'}")
    print(f"  Segment time series -> {output_dir / 'sam_employment_segment_timeseries.csv'}")
    print(f"  Stage time series -> {output_dir / 'sam_employment_stage_timeseries.csv'}")
    print(f"  Occupation forecasts -> {occ_full_path}")
    print(f"  Occupation 2030 snapshot -> {occ_2030_path}")
    print(f"  Stage 2030 snapshot -> {stage_occ_path}")
    print(f"  Validation -> {occ_val_path}")


if __name__ == "__main__":
    main()

