from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from process_moodys_time_series import read_wide

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = REPO_ROOT / "data" / "interim" / "moodys_mi_annual_multipliers_2024_2034.csv"


def load_moodys_mi_employment() -> pd.DataFrame:
    df, year_cols = read_wide()
    geo_df = df[(df["Geography:"].astype(str).str.strip() == "Michigan") & (df["metric"] == "employment")].copy()
    geo_df["naics_code"] = geo_df["naics_code"].astype(str)
    long_df = geo_df.melt(
        id_vars=["naics_code", "Description:"],
        value_vars=year_cols,
        var_name="year",
        value_name="employment",
    )
    long_df["year"] = pd.to_datetime(long_df["year"], errors="coerce").dt.year
    long_df = long_df.dropna(subset=["year"])
    long_df["employment"] = pd.to_numeric(long_df["employment"], errors="coerce")
    long_df = long_df.dropna(subset=["employment"])
    long_df.rename(columns={"Description:": "description"}, inplace=True)
    return long_df


def compute_multipliers(long_df: pd.DataFrame) -> pd.DataFrame:
    target_years = list(range(2023, 2035))
    filtered = long_df[long_df["year"].isin(target_years)].copy()
    if filtered.empty:
        return pd.DataFrame()

    filtered.sort_values(["naics_code", "year"], inplace=True)
    filtered["yoy_multiplier"] = filtered.groupby("naics_code")["employment"].transform(lambda s: s / s.shift(1))
    filtered["yoy_pct_change"] = (filtered["yoy_multiplier"] - 1.0) * 100.0
    filtered = filtered[filtered["year"].between(2024, 2034)]
    return filtered[["naics_code", "description", "year", "employment", "yoy_multiplier", "yoy_pct_change"]]


def main() -> None:
    long_df = load_moodys_mi_employment()
    output = compute_multipliers(long_df)
    if output.empty:
        raise RuntimeError("No Moody's multipliers computed. Check source data.")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(OUTPUT, index=False)
    print(f"Saved {OUTPUT}")


if __name__ == "__main__":
    main()





