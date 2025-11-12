from __future__ import annotations

from pathlib import Path
from typing import Dict

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SAM_DIR = REPO_ROOT / "data" / "processed" / "sam_auto_dashboard"
INTERIM_DIR = REPO_ROOT / "data" / "interim"
EXPORT_DIR = REPO_ROOT / "reports" / "sam_dashboard_outputs"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

SEGMENT_TS_PATH = SAM_DIR / "sam_employment_segment_timeseries.csv"
MOODYS_COMPARISON_MI = INTERIM_DIR / "moodys_growth_comparison_mi.csv"
MOODYS_COMPARISON_US = INTERIM_DIR / "moodys_growth_comparison_us.csv"

UPJOHN_TEAL = "#2B9CB4"
PALETTE = {
    "moodys_mi": "#2B9CB4",
    "moodys_us": "#004A5E",
    "dtmb_mi": "#AF2C32",
    "bls_us": "#7A7A7A",
}

PROJECTION_LABELS: Dict[str, str] = {
    "moodys_mi": "Moody's MI (flat CAGR)",
    "dtmb_mi": "DTMB MI",
    "bls_us": "BLS US",
}


def load_segment_series() -> pd.DataFrame:
    df = pd.read_csv(SEGMENT_TS_PATH)
    df["forecast_source"] = df["forecast_source"].astype(str)
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype(int)
    df = df[df["forecast_source"] != "moodys_us"].copy()
    df["method_label"] = df["forecast_source"].map(PROJECTION_LABELS).fillna(df["forecast_source"])
    return df


def make_segment_timeline_plot(df: pd.DataFrame, segment_id: int, metric: str) -> Path:
    segment_rows = df[df["segment_id"] == segment_id]
    if segment_rows.empty:
        raise RuntimeError(f"No data for segment {segment_id}")
    segment_name = segment_rows["segment_name"].iloc[0]
    value_col = "employment_auto" if metric == "SAM-adjusted" else "employment_raw"

    fig, ax = plt.subplots(figsize=(12, 6), dpi=150)
    ax.set_facecolor("#F7F9FB")

    for slug, label in PROJECTION_LABELS.items():
        subset = (
            segment_rows[segment_rows["forecast_source"] == slug]
            .groupby("year", as_index=False)[value_col]
            .sum()
        )
        if subset.empty:
            continue
        ax.plot(
            subset["year"],
            subset[value_col],
            label=label,
            color=PALETTE.get(slug, "#999999"),
            linewidth=2.2,
            marker="o",
            markersize=4,
        )

    ax.set_title(f"{segment_name}\n{metric} employment (2001–2034)", fontsize=16, color="#1F2A33", pad=15)
    ax.set_xlabel("Year", fontsize=12, color="#1F2A33")
    ax.set_ylabel("Employment", fontsize=12, color="#1F2A33")
    ax.yaxis.set_major_formatter(ticker.StrMethodFormatter("{x:,.0f}"))
    ax.grid(axis="y", color="#E1E8ED", linewidth=0.9, alpha=0.7)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(frameon=False, fontsize=11, loc="upper left")

    safe_name = segment_name.lower().replace(" ", "_").replace("/", "_").replace("&", "and")
    metric_tag = "auto" if metric == "SAM-adjusted" else "raw"
    out_path = EXPORT_DIR / f"segment_timeline_{safe_name}_{metric_tag}.png"
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    return out_path


def load_moodys_comparison(geo: str) -> pd.DataFrame:
    path = MOODYS_COMPARISON_MI if geo == "mi" else MOODYS_COMPARISON_US
    if not path.exists():
        raise FileNotFoundError(f"Moody's comparison file missing: {path}")
    df = pd.read_csv(path)
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype(int)
    return df


def make_moodys_growth_plot(geo: str) -> Path:
    comparison = load_moodys_comparison(geo)
    geo_label = "Michigan" if geo == "mi" else "United States"
    summary = (
        comparison.groupby("year")
        .agg(actual_total=("actual_employment", "sum"), flat_total=("flat_employment", "sum"))
        .reset_index()
    )

    fig, ax = plt.subplots(figsize=(12, 6), dpi=150)
    ax.plot(summary["year"], summary["actual_total"], label="Moody's actual path", color=UPJOHN_TEAL, linewidth=2.4)
    ax.plot(
        summary["year"],
        summary["flat_total"],
        label="Flat 6-year CAGR path",
        color="#AF2C32",
        linewidth=2.2,
        linestyle="--",
    )

    ax.set_title(f"Moody's annual employment path — {geo_label}", fontsize=16, color="#1F2A33", pad=15)
    ax.set_xlabel("Year", fontsize=12, color="#1F2A33")
    ax.set_ylabel("Employment (Moody's units)", fontsize=12, color="#1F2A33")
    ax.yaxis.set_major_formatter(ticker.StrMethodFormatter("{x:,.0f}"))
    ax.grid(axis="y", color="#E1E8ED", linewidth=0.9, alpha=0.7)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(frameon=False, fontsize=11, loc="upper left")
    fig.tight_layout()

    out_path = EXPORT_DIR / f"moodys_growth_{geo}.png"
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    return out_path


def main() -> None:
    df = load_segment_series()
    for segment_id in sorted(df["segment_id"].unique()):
        if segment_id == 0:
            continue
        for metric in ["SAM-adjusted", "Raw"]:
            path = make_segment_timeline_plot(df, segment_id, metric)
            print(f"Saved {path}")

    path = make_moodys_growth_plot("mi")
    print(f"Saved {path}")


if __name__ == "__main__":
    main()
