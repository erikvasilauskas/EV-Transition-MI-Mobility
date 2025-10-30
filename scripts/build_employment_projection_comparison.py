"""Compile employment projection rates from multiple sources into a tidy table.

Sources:
- data/raw/naics-level-employment-projections.csv

Outputs:
- data/intermediate/employment_projection_comparison.csv
  Contains NAICS metadata plus six-year employment change rates from
  Moody's (MI & US), DTMB (MI), and BLS (US), all expressed as decimal
  proportions.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def _as_numeric(series: pd.Series) -> pd.Series:
    """Convert strings with commas or parentheses to floats."""
    cleaned = (
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("(", "-")
        .str.replace(")", "")
        .str.strip()
    )
    cleaned = cleaned.replace({"": np.nan, "nan": np.nan})
    return pd.to_numeric(cleaned, errors="coerce")


def _percent_to_decimal(series: pd.Series) -> pd.Series:
    return _as_numeric(series).div(100.0)


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    raw_path = repo_root / "data" / "raw" / "naics-level-employment-projections.csv"
    output_path = repo_root / "data" / "intermediate" / "employment_projection_comparison.csv"

    df = pd.read_csv(raw_path, dtype={"naics_code": str})
    df["naics_code"] = df["naics_code"].str.strip().str.zfill(4)

    df["employment_mi_qcew_raw_2024"] = _as_numeric(df["employment_mi_qcew_raw_2024"])
    df["moodys_mi_pct_change_2024_2030_employment"] = _percent_to_decimal(
        df["moodys_mi_pct_change_2024_2030_employment"]
    )
    df["moodys_us_pct_change_2024_2030_employment"] = _percent_to_decimal(
        df["moodys_us_pct_change_2024_2030_employment"]
    )
    df["mi_dtmb_six_year_rate"] = _percent_to_decimal(df["mi_dtmb_ind_proj_22_32_six_year_rate"])
    df["bls_us_six_year_employment_rate_change"] = _percent_to_decimal(
        df["bls_us_six_year_employment_rate_change"]
    )

    columns = [
        "orig_sort",
        "naics_code",
        "industry_name",
        "segment_id",
        "segment_name",
        "stage",
        "employment_mi_qcew_raw_2024",
        "moodys_mi_pct_change_2024_2030_employment",
        "moodys_us_pct_change_2024_2030_employment",
        "mi_dtmb_six_year_rate",
        "bls_us_six_year_employment_rate_change",
    ]

    result = df[columns].rename(
        columns={
            "industry_name": "naics_title",
            "employment_mi_qcew_raw_2024": "employment_qcew_2024",
        }
    )

    result.to_csv(output_path, index=False)
    print(f"Wrote employment projection comparison to {output_path}")


if __name__ == "__main__":
    main()
