# -*- coding: utf-8 -*-
"""Generate segment and stage employment plots (2000-2030) for the refreshed 2024 dashboard."""

from __future__ import annotations

from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_YEAR = 2024
MONTHLY_PATH = REPO_ROOT / "data/raw/qcew_auto_employment_monthly_clean.csv"
SAM_SHARES_PATH = (
    REPO_ROOT / "data/intermediate/sam_naics_shares_v2/sam_auto_naics4_mobility38.csv"
)
SEGMENT_TIMESERIES_PATH = (
    REPO_ROOT / "data/processed/sam_auto_dashboard_2024_refresh/sam_employment_segment_timeseries.csv"
)
STAGE_TIMESERIES_PATH = (
    REPO_ROOT / "data/processed/sam_auto_dashboard_2024_refresh/sam_employment_stage_timeseries.csv"
)
OUTPUT_DIR = (
    REPO_ROOT
    / "data"
    / "processed"
    / "sam_auto_dashboard_2024_refresh"
    / "plots_refresh"
)

OEM_NAICS = {"5413", "5414", "5417"}
TARGET_STAGE = {"upstream"}
HISTORICAL_END = pd.Timestamp(BASE_YEAR, 12, 1)
SCENARIOS = {
    # Use common Moody's MI CAGR (not the detailed annual path)
    "moodys_mi": ("Moody's MI", "#0067a0"),
    "bls_us": ("BLS US", "#dd8452"),
    "dtmb_mi": ("DTMB MI", "#55a868"),
}
FORECAST_YEARS = [2025, 2026, 2027, 2028, 2029, 2030]

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
}
STAGE_LABEL_OVERRIDES = {
    "oem": "OEM",
    "upstream": "Upstream",
    "downstream": "Downstream",
    "upstream + core/oem": "Upstream + Core/OEM",
}


def load_monthly_history() -> tuple[pd.DataFrame, pd.DataFrame]:
    monthly = pd.read_csv(MONTHLY_PATH, parse_dates=["period"])
    monthly = monthly[monthly["row_type"] == "naics_detail"].copy()
    if "stage" in monthly.columns:
        monthly = monthly.drop(columns=["stage"])
    monthly["naics_code"] = (
        monthly["naics_code"].astype(str).str.strip().str.zfill(4)
    )

    shares = pd.read_csv(SAM_SHARES_PATH, dtype={"naics_code": str})
    shares.columns = shares.columns.str.strip()
    shares["naics_code"] = shares["naics_code"].str.strip().str.zfill(4)
    shares["segment_name"] = shares["segment_name"].astype(str)
    monthly = monthly.merge(
        shares[
            [
                "naics_code",
                "segment_id",
                "segment_name",
                "stage",
                "auto_share_of_output",
            ]
        ],
        on="naics_code",
        how="inner",
        suffixes=("", ""),
    )
    monthly["segment_id"] = pd.to_numeric(monthly["segment_id"], errors="coerce").astype("Int64")
    monthly = monthly.dropna(subset=["segment_id"])
    monthly["segment_id"] = monthly["segment_id"].astype(int)
    monthly["segment_label"] = monthly["segment_id"].map(SEGMENT_LABELS).fillna(
        monthly["segment_name"].astype(str)
    )
    monthly["stage_lower"] = monthly["stage"].astype(str).str.lower().str.strip()
    share = monthly["auto_share_of_output"].fillna(0.0).clip(0.0, 1.0)
    target_mask = monthly["stage_lower"].isin(TARGET_STAGE) | monthly[
        "naics_code"
    ].isin(OEM_NAICS)
    monthly["share_applied"] = np.where(target_mask, share, 1.0)
    monthly["employment_auto"] = monthly["employment"] * monthly["share_applied"]

    segment_hist = (
        monthly.groupby(["segment_id", "segment_label", "period"], as_index=False)[
            "employment_auto"
        ].sum()
    )
    segment_hist.rename(columns={"segment_label": "segment_name"}, inplace=True)
    stage_hist = (
        monthly.groupby(["stage_lower", "period"], as_index=False)[
            "employment_auto"
        ].sum()
    )
    stage_hist.rename(columns={"stage_lower": "stage"}, inplace=True)
    stage_hist = stage_hist[stage_hist["stage"].astype(str).str.len() > 0]
    return segment_hist, stage_hist


def load_forecast_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    seg = pd.read_csv(SEGMENT_TIMESERIES_PATH)
    stage = pd.read_csv(STAGE_TIMESERIES_PATH)
    seg = seg[seg["year"].isin(FORECAST_YEARS)].copy()
    stage = stage[stage["year"].isin(FORECAST_YEARS)].copy()
    seg["period"] = pd.to_datetime(seg["year"].astype(str) + "-01-01")
    stage["period"] = pd.to_datetime(stage["year"].astype(str) + "-01-01")
    stage["stage"] = stage["stage"].astype(str).str.lower()
    return seg, stage


def plot_entity(
    entity: str,
    name: str,
    hist_df: pd.DataFrame,
    forecast_df: pd.DataFrame,
    kind: str,
):
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(
        hist_df["period"],
        hist_df["employment_auto"],
        color="#222222",
        label="Historical",
        linewidth=1.5,
    )

    for slug, (label, color) in SCENARIOS.items():
        subset = forecast_df[forecast_df["forecast_source"] == slug]
        if subset.empty:
            continue
        ax.plot(
            subset["period"],
            subset["employment_auto"],
            color=color,
            marker="o",
            linestyle="-",
            linewidth=1,
            label=label,
        )

    ax.axvline(HISTORICAL_END, color="#555555", linestyle="--", linewidth=1)
    title_text = f"{name} Employment (2000–2030)"
    if name.lower().startswith("oem") or name.lower().startswith("core automotive"):
        title_text = "Core Automotive Employment (2000-2030)"
    ax.set_title(title_text)
    ax.set_ylabel("Employment")
    ax.set_xlabel("Year")
    ax.legend()
    ax.xaxis.set_major_locator(mdates.YearLocator(base=5))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.grid(True, linestyle=":", linewidth=0.4, alpha=0.7)
    fig.tight_layout()
    filename = OUTPUT_DIR / f"{kind}_{entity.replace(' ', '_')}.png"
    fig.savefig(filename, dpi=200)
    plt.close(fig)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    segment_hist, stage_hist = load_monthly_history()
    seg_forecast, stage_forecast = load_forecast_tables()

    for seg_id, group in segment_hist.groupby("segment_id"):
        name = group["segment_name"].iloc[0]
        forecast_subset = seg_forecast[seg_forecast["segment_id"] == seg_id]
        if forecast_subset.empty:
            continue
        plot_entity(
            entity=f"segment_{int(seg_id)}",
            name=name,
            hist_df=group.sort_values("period"),
            forecast_df=forecast_subset.sort_values("period"),
            kind="segment",
        )

    for stage_name, group in stage_hist.groupby("stage"):
        label = STAGE_LABEL_OVERRIDES.get(stage_name, stage_name.title())
        forecast_subset = stage_forecast[stage_forecast["stage"] == stage_name]
        if forecast_subset.empty:
            continue
        plot_entity(
            entity=f"stage_{label.replace(' ', '_')}",
            name=label,
            hist_df=group.sort_values("period"),
            forecast_df=forecast_subset.sort_values("period"),
            kind="stage",
        )

    print(f"Wrote plots to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
