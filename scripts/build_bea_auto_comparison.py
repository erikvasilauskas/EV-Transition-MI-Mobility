#!/usr/bin/env python3
"""
Compare legacy BEA attribution shares with detailed commodity-based shares.

Inputs
------
- data/interim/bea_domestic_use_target_naics_summary.csv
    Output from build_bea_domestic_use_targets.py containing commodity-based shares.
- data/raw/auto_attribution_bea.csv
    Previously curated BEA share table based on summary data.

Output
------
- data/interim/bea_auto_attribution_comparison.csv
    Combined table with both share sources aligned by NAICS code and segment metadata.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_new_shares(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"NAICS": str})
    df["NAICS"] = df["NAICS"].str.strip().str.zfill(4)
    return df[
        [
            "NAICS",
            "naics_title",
            "segment_id",
            "segment_name",
            "stage",
            "share_of_intermediate_inputs",
            "share_of_total_commodity_output",
        ]
    ]


def load_legacy_shares(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"NAICS": str})
    df["NAICS"] = df["NAICS"].str.strip().str.zfill(4)
    df = df.rename(
        columns={
            "NAICS Title": "legacy_naics_title",
            "bea_share_to_set": "legacy_bea_share_to_set",
            "Stage": "legacy_stage",
            "Sector": "legacy_sector",
        }
    )
    return df


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]

    summary_path = repo_root / "data" / "interim" / "bea_domestic_use_target_naics_summary.csv"
    legacy_path = repo_root / "data" / "raw" / "auto_attribution_bea.csv"
    output_path = repo_root / "data" / "interim" / "bea_auto_attribution_comparison.csv"

    new_df = load_new_shares(summary_path)
    legacy_df = load_legacy_shares(legacy_path)

    merged = legacy_df.merge(new_df, on="NAICS", how="outer", indicator=True)
    merged.rename(columns={"NAICS": "naics_code"}, inplace=True)

    merged.rename(
        columns={
            "_merge": "merge_status",
        },
        inplace=True,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(output_path, index=False)


if __name__ == "__main__":
    main()

