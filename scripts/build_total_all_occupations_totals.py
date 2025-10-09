#!/usr/bin/env python3
"""
Combine the "Total, all occupations" (00-0000) rows from the US staffing pattern
tables and compute additional growth metrics.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Dict, Iterable, List


def read_total_rows(source_files: Iterable[Path]) -> List[Dict[str, str]]:
    """Collect rows where Occupation Code equals 00-0000 from the provided files."""
    total_rows: List[Dict[str, str]] = []

    for path in sorted(source_files):
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                continue

            for row in reader:
                if row.get("Occupation Code") == "00-0000":
                    total_rows.append(row)
                    break

    return total_rows


def compute_growth_rates(row: Dict[str, str]) -> Dict[str, str]:
    """Compute annual and six-year growth rates based on 2024 and 2034 employment."""
    emp_2024_raw = row.get("2024 Employment", "")
    emp_2034_raw = row.get("Projected 2034 Employment", "")

    try:
        emp_2024 = float(emp_2024_raw.replace(",", ""))
        emp_2034 = float(emp_2034_raw.replace(",", ""))
    except ValueError:
        return {
            "annual_employment_rate_change": "",
            "six_year_employment_rate_change": "",
        }

    if emp_2024 <= 0.0 or emp_2034 < 0.0:
        return {
            "annual_employment_rate_change": "",
            "six_year_employment_rate_change": "",
        }

    annual_rate = (math.pow(emp_2034 / emp_2024, 0.1) - 1.0) * 100
    six_year_rate = (math.pow(1.0 + (annual_rate/100), 6) - 1.0) * 100

    return {
        "annual_employment_rate_change": f"{annual_rate:.6f}",
        "six_year_employment_rate_change": f"{six_year_rate:.6f}",
    }


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source_dir = repo_root / "data" / "raw" / "us_staffing_patterns"
    output_path = repo_root / "data" / "interim" / "us_staffing_total_all_occupations.csv"

    source_files = list(source_dir.glob("us_staffing_*.csv"))
    if not source_files:
        raise FileNotFoundError(f"No source files found in {source_dir}")

    total_rows = read_total_rows(source_files)
    if not total_rows:
        raise ValueError("No rows with Occupation Code 00-0000 were found.")

    fieldnames = list(total_rows[0].keys()) + [
        "annual_employment_rate_change",
        "six_year_employment_rate_change",
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in total_rows:
            row_with_rates = row.copy()
            row_with_rates.update(compute_growth_rates(row))
            writer.writerow(row_with_rates)


if __name__ == "__main__":
    main()

