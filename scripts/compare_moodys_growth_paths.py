import argparse
from pathlib import Path

import numpy as np
import pandas as pd

# Reuse the Moody’s workbook reader from process_moodys_time_series
from process_moodys_time_series import REPO_ROOT, read_wide

INTERIM_DIR = REPO_ROOT / "data" / "interim"
OUTPUT_COMPARISON = INTERIM_DIR / "moodys_growth_comparison_{geo}.csv"
OUTPUT_SUMMARY = INTERIM_DIR / "moodys_growth_summary_{geo}.csv"

GEOGRAPHY_LABELS = {
    "mi": "Michigan",
    "michigan": "Michigan",
    "us": "United States",
    "usa": "United States",
    "united_states": "United States",
}

INTERIM_CAGR_FILES = {
    "Michigan": INTERIM_DIR / "moodys_michigan_2024_2030.csv",
    "United States": INTERIM_DIR / "moodys_us_2024_2030.csv",
}


def load_naics_employment(geography: str) -> pd.DataFrame:
    df, year_cols = read_wide()
    geo_df = df[(df["Geography:"].str.strip() == geography) & (df["metric"] == "employment")].copy()
    if geo_df.empty:
        raise ValueError(f"No employment rows found for geography '{geography}'. Available: {sorted(df['Geography:'].unique())}")

    long = geo_df.melt(
        id_vars=["naics_code", "Description:"],
        value_vars=year_cols,
        var_name="year_raw",
        value_name="employment",
    ).dropna(subset=["employment"])

    long["year"] = pd.to_datetime(long["year_raw"]).dt.year
    long["naics_code"] = long["naics_code"].astype(str).str.zfill(4)
    long.rename(columns={"Description:": "description"}, inplace=True)
    return long[["naics_code", "description", "year", "employment"]]


def compute_flat_path(base_value: float, total_rate: float, years_ahead: int) -> float:
    if years_ahead <= 0:
        return base_value
    if total_rate <= -1:
        return 0.0
    cagr = np.power(1.0 + total_rate, years_ahead / 6.0)
    return base_value * cagr


def build_comparison(geography: str, start_year: int, end_year: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    long_df = load_naics_employment(geography)
    long_df = long_df[(long_df["year"] >= start_year - 1) & (long_df["year"] <= end_year)].copy()

    pivot = (
        long_df.pivot_table(index=["naics_code", "description"], columns="year", values="employment")
        .sort_index()
    )

    cagr_path = INTERIM_CAGR_FILES.get(geography)
    if not cagr_path or not cagr_path.exists():
        raise FileNotFoundError(f"Missing Moody's comparison file for {geography}: {cagr_path}")

    cagr_df = pd.read_csv(cagr_path, dtype={"naics_code": str})
    if "pct_change_2024_2030_employment" not in cagr_df.columns:
        raise KeyError("Expected column 'pct_change_2024_2030_employment' in comparison file.")
    cagr_df["pct_change_2024_2030_employment"] = (
        pd.to_numeric(cagr_df["pct_change_2024_2030_employment"], errors="coerce") / 100.0
    )
    rate_lookup = cagr_df.set_index("naics_code")["pct_change_2024_2030_employment"].to_dict()
    base_lookup = cagr_df.set_index("naics_code")[f"{start_year}_employment"].to_dict()

    records: list[dict[str, float]] = []
    years = list(range(start_year, end_year + 1))

    for (naics, desc), row in pivot.iterrows():
        if naics not in rate_lookup or naics not in base_lookup:
            continue
        base_value = row.get(start_year)
        if pd.isna(base_value):
            base_value = base_lookup.get(naics)
        if pd.isna(base_value):
            continue
        total_rate = rate_lookup.get(naics, 0.0)

        prev_actual = np.nan
        prev_flat = np.nan

        for year in years:
            actual_val = row.get(year)
            flat_val = compute_flat_path(base_value, total_rate, year - start_year)

            actual_yoy = np.nan
            flat_yoy = np.nan
            if not pd.isna(prev_actual) and not pd.isna(actual_val) and prev_actual != 0:
                actual_yoy = (actual_val / prev_actual) - 1.0
            if not pd.isna(prev_flat) and prev_flat != 0:
                flat_yoy = (flat_val / prev_flat) - 1.0

            records.append(
                {
                    "geography": geography,
                    "naics_code": naics,
                    "description": desc,
                    "year": year,
                    "actual_employment": actual_val,
                    "flat_employment": flat_val,
                    "actual_yoy": actual_yoy,
                    "flat_yoy": flat_yoy,
                    "employment_diff": (actual_val - flat_val) if not pd.isna(actual_val) else np.nan,
                }
            )

            prev_actual = actual_val
            prev_flat = flat_val

    comparison = pd.DataFrame.from_records(records)
    if comparison.empty:
        raise RuntimeError("No overlapping NAICS between Moody's time series and comparison file.")

    summary = (
        comparison.groupby("year")
        .agg(
            actual_total=("actual_employment", "sum"),
            flat_total=("flat_employment", "sum"),
            mean_abs_diff=("employment_diff", lambda s: np.nanmean(np.abs(s))),
        )
        .reset_index()
    )
    summary["diff_total"] = summary["actual_total"] - summary["flat_total"]
    summary["pct_diff_total"] = np.where(
        summary["flat_total"] != 0,
        (summary["diff_total"] / summary["flat_total"]) * 100,
        np.nan,
    )

    return comparison, summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare Moody's actual NAICS growth to flat CAGR paths.")
    parser.add_argument(
        "--geography",
        default="mi",
        help="Geography key (mi or us). Defaults to Michigan.",
    )
    parser.add_argument(
        "--start-year",
        type=int,
        default=2024,
        help="Base year for comparison (default 2024).",
    )
    parser.add_argument(
        "--end-year",
        type=int,
        default=2034,
        help="Ending year for comparison (default 2034).",
    )
    args = parser.parse_args()

    geo_key = args.geography.lower()
    if geo_key not in GEOGRAPHY_LABELS:
        raise ValueError(f"Unsupported geography '{args.geography}'. Expected one of: {sorted(GEOGRAPHY_LABELS)}")
    geography = GEOGRAPHY_LABELS[geo_key]

    comparison, summary = build_comparison(geography, args.start_year, args.end_year)

    comp_path = OUTPUT_COMPARISON.with_name(OUTPUT_COMPARISON.name.format(geo=geo_key))
    summary_path = OUTPUT_SUMMARY.with_name(OUTPUT_SUMMARY.name.format(geo=geo_key))
    comparison.to_csv(comp_path, index=False)
    summary.to_csv(summary_path, index=False)

    print(f"Saved detailed comparison to {comp_path}")
    print(f"Saved summary stats to {summary_path}")

    print("\nSummary preview:")
    print(summary)


if __name__ == "__main__":
    main()
