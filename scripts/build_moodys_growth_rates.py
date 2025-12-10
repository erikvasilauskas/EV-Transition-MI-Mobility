"""Compute Moody's growth rates (CAGR 2024–2030 and YoY) for MI and US.

Uses the updated Moody's workbook (December 2025) via `process_moodys_time_series.read_wide`.
Outputs:
  - data/interim/moodys_growth_cagr_2024_2030.csv
  - data/interim/moodys_growth_yoy_2024_2030.csv
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from process_moodys_time_series import read_wide

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = REPO_ROOT / "data" / "interim"
BASE_YEAR = 2024
TARGET_YEAR = 2030
YEARS = (BASE_YEAR, TARGET_YEAR)
GEO_KEEP = {"United States", "Michigan"}
METRICS = ("employment", "wages", "gdp")


def load_long() -> pd.DataFrame:
    df, year_cols = read_wide()
    df = df[df["Geography:"].isin(GEO_KEEP)]
    long = df.melt(
        id_vars=["naics_code", "metric", "Geography:"],
        value_vars=year_cols,
        var_name="date",
        value_name="value",
    )
    long["year"] = pd.to_datetime(long["date"], errors="coerce").dt.year
    long = long.drop(columns=["date"])
    long["value"] = pd.to_numeric(long["value"], errors="coerce")
    long = long[long["metric"].isin(METRICS)]
    return long.dropna(subset=["year", "value"])


def compute_cagr(long_df: pd.DataFrame) -> pd.DataFrame:
    base = long_df[long_df["year"] == BASE_YEAR].set_index(["Geography:", "naics_code", "metric"])["value"]
    target = long_df[long_df["year"] == TARGET_YEAR].set_index(["Geography:", "naics_code", "metric"])["value"]
    joined = base.to_frame("value_base").join(target.to_frame("value_target"), how="inner")
    years_span = TARGET_YEAR - BASE_YEAR
    for col in ["value_base", "value_target"]:
        joined[col] = pd.to_numeric(joined[col], errors="coerce")
    cagr = (joined["value_target"] / joined["value_base"].replace({0: pd.NA})) ** (1 / years_span) - 1
    cagr[joined["value_base"] == 0] = pd.NA
    joined["cagr_pct"] = cagr * 100
    joined = joined.reset_index()
    return joined[["Geography:", "naics_code", "metric", "value_base", "value_target", "cagr_pct"]]


def compute_yoy(long_df: pd.DataFrame) -> pd.DataFrame:
    records = []
    for keys, group in long_df.groupby(["Geography:", "naics_code", "metric"]):
        group = group.sort_values("year")
        vals = pd.to_numeric(group["value"], errors="coerce")
        prev = vals.shift(1)
        yoy = (vals - prev) / prev * 100
        yoy[prev == 0] = pd.NA
        rec = group[["Geography:", "naics_code", "metric", "year"]].copy()
        rec["yoy_pct"] = yoy.values
        records.append(rec)
    if not records:
        return pd.DataFrame(columns=["Geography:", "naics_code", "metric", "year", "yoy_pct"])
    return pd.concat(records, ignore_index=True)


def main() -> None:
    long_df = load_long()
    cagr_df = compute_cagr(long_df)
    yoy_df = compute_yoy(long_df)
    yoy_df = yoy_df[yoy_df["year"].between(BASE_YEAR, TARGET_YEAR)]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    cagr_path = OUTPUT_DIR / "moodys_growth_cagr_2024_2030.csv"
    yoy_path = OUTPUT_DIR / "moodys_growth_yoy_2024_2030.csv"
    cagr_df.to_csv(cagr_path, index=False)
    yoy_df.to_csv(yoy_path, index=False)
    print(f"Wrote {cagr_path}")
    print(f"Wrote {yoy_path}")


if __name__ == "__main__":
    main()
