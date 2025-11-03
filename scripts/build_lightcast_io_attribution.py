"""Generate Lightcast-style automotive attribution shares for MI and US matrices.

This script reproduces the three attribution variants that were previously run
outside the repository in R:

* Core automotive buyers (NAICS 3361-3363)
* Mobility supply-chain buyer set (the 38 NAICS in our lookup file)
* Weighted buyer set (core auto = 1.0, others weighted by their core share)

Inputs (all under ``data/raw``):

* ``mi_regional_matrix_cleaned_industries.csv``
* ``us_regional_matrix_cleaned_industries.csv``
* ``emp_2024_10.csv`` (injested for stage/segment labels)

Outputs are written to ``data/intermediate/lightcast_io_shares`` for both MI
and US matrices, followed by regeneration of the consolidated comparison table
and associated plot.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import runpy

RE_NAICS = re.compile(r"(\d{4,6})")
CORE_AUTO_NAICS = {"3361", "3362", "3363"}


def repo_path(*parts: str) -> Path:
    return Path(__file__).resolve().parents[1].joinpath(*parts)


def clean_naics(value: str | int | float | None, digits: int = 4) -> str | None:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    text = str(value)
    match = RE_NAICS.search(text)
    if not match:
        return None
    return match.group(1)[:digits].rjust(digits, "0")


def load_employment(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str)
    df.columns = df.columns.str.strip()

    df["naics4"] = df["NAICS"].apply(clean_naics)
    df["naics_title"] = (
        df.get("NAICS Title", "")
        .astype(str)
        .str.strip()
        .str.strip('"')
        .str.replace("  ", " ", regex=False)
    )
    df["Stage"] = df.get("Stage", "").astype(str).str.strip()
    df["Sector"] = df.get("Sector", "").astype(str).str.strip()
    df["emp"] = (
        df.get("TOT_EMP", "")
        .astype(str)
        .str.replace(",", "", regex=False)
        .replace({"": np.nan})
        .pipe(pd.to_numeric, errors="coerce")
        .fillna(0.0)
    )

    df = df.dropna(subset=["naics4"])
    df = df.sort_values(["naics4", "Stage", "Sector"])
    meta = df.drop_duplicates("naics4", keep="first")[
        ["naics4", "Stage", "Sector", "naics_title", "emp"]
    ].copy()
    meta["Stage"] = meta["Stage"].replace({"": "Unknown"})
    meta["Sector"] = meta["Sector"].replace({"": "Unknown"})
    return meta.reset_index(drop=True)


def load_matrix(path: Path) -> tuple[pd.DataFrame, pd.Series, list[str], dict[str, str]]:
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip()

    buyer_cols = [c for c in df.columns if c != "Sector"]
    numeric = df[buyer_cols].apply(pd.to_numeric, errors="coerce").fillna(0.0)

    supplier6 = df["Sector"].astype(str).str.replace(r"^z[.\|]", "", regex=True)
    supplier4 = supplier6.str[:4]

    buyer_map = {
        col: re.sub(r"^z[.\|]", "", col) for col in buyer_cols
    }
    buyer_naics4 = {col: code[:4] for col, code in buyer_map.items()}

    return numeric, supplier4, buyer_cols, buyer_naics4


def aggregate_by_supplier(
    numerator: pd.Series | np.ndarray,
    denominator: pd.Series | np.ndarray,
    supplier4: pd.Series,
) -> pd.DataFrame:
    if isinstance(numerator, pd.Series):
        numerator = numerator.to_numpy()
    if isinstance(denominator, pd.Series):
        denominator = denominator.to_numpy()
    df = pd.DataFrame(
        {
            "supplier4": supplier4.values,
            "num_to_set": numerator,
            "denom_total": denominator,
        }
    )
    grouped = (
        df.groupby("supplier4", as_index=False)
        .sum(numeric_only=True)
        .assign(
            share_to_set=lambda d: np.where(
                d["denom_total"] > 0, d["num_to_set"] / d["denom_total"], 0.0
            )
        )
    )
    return grouped


def compute_core_shares(
    numeric: pd.DataFrame,
    supplier4: pd.Series,
    buyer_cols: list[str],
    buyer_naics4: dict[str, str],
) -> pd.DataFrame:
    mask = [buyer_naics4[col] in CORE_AUTO_NAICS for col in buyer_cols]
    numerator = numeric.loc[:, mask].sum(axis=1)
    denominator = numeric.sum(axis=1)
    return aggregate_by_supplier(numerator, denominator, supplier4)


def compute_supply_chain_shares(
    numeric: pd.DataFrame,
    supplier4: pd.Series,
    buyer_cols: list[str],
    buyer_naics4: dict[str, str],
    supply_chain_naics: Iterable[str],
) -> pd.DataFrame:
    supply_chain_set = set(supply_chain_naics)
    mask = [buyer_naics4[col] in supply_chain_set for col in buyer_cols]
    numerator = numeric.loc[:, mask].sum(axis=1)
    denominator = numeric.sum(axis=1)
    return aggregate_by_supplier(numerator, denominator, supplier4)


def compute_weighted_shares(
    numeric: pd.DataFrame,
    supplier4: pd.Series,
    buyer_cols: list[str],
    buyer_naics4: dict[str, str],
    weights: dict[str, float],
) -> pd.DataFrame:
    valid_cols = [
        (idx, buyer_cols[idx], buyer_naics4[buyer_cols[idx]])
        for idx in range(len(buyer_cols))
        if buyer_naics4[buyer_cols[idx]] in weights
    ]
    if not valid_cols:
        empty = pd.DataFrame(columns=["supplier4", "num_to_set", "denom_total", "share_to_set"])
        return empty

    indices, selected_cols, naics_vals = zip(*valid_cols)
    weight_array = np.array([np.clip(weights[code], 0.0, 1.0) for code in naics_vals])

    subset = numeric.iloc[:, list(indices)].to_numpy()
    numerator = subset.dot(weight_array)
    denominator = numeric.sum(axis=1).to_numpy()
    return aggregate_by_supplier(numerator, denominator, supplier4)


def attach_metadata(shares: pd.DataFrame, employment: pd.DataFrame) -> pd.DataFrame:
    meta = employment.rename(columns={"naics4": "supplier4"})
    merged = meta.merge(shares, on="supplier4", how="right")
    merged = merged.rename(columns={"supplier4": "naics4"})
    cols = [
        "Stage",
        "Sector",
        "naics4",
        "naics_title",
        "emp",
        "num_to_set",
        "denom_total",
        "share_to_set",
    ]
    for col in cols:
        if col not in merged.columns:
            merged[col] = np.nan
    merged = merged[cols].sort_values("share_to_set", ascending=False).reset_index(drop=True)
    return merged


def compute_region_outputs(matrix_path: Path, employment: pd.DataFrame) -> dict[str, pd.DataFrame]:
    numeric, supplier4, buyer_cols, buyer_naics4 = load_matrix(matrix_path)
    core = compute_core_shares(numeric, supplier4, buyer_cols, buyer_naics4)
    supply_chain_naics = employment["naics4"].unique()
    supply_chain = compute_supply_chain_shares(
        numeric, supplier4, buyer_cols, buyer_naics4, supply_chain_naics
    )

    core_weights = dict(zip(core["supplier4"], core["share_to_set"]))
    weighted_buyers = {
        naics: (1.0 if naics in CORE_AUTO_NAICS else core_weights.get(naics, 0.0))
        for naics in supply_chain_naics
    }
    weighted = compute_weighted_shares(numeric, supplier4, buyer_cols, buyer_naics4, weighted_buyers)

    return {
        "core": attach_metadata(core, employment),
        "supply_chain": attach_metadata(supply_chain, employment),
        "weighted": attach_metadata(weighted, employment),
    }


def write_outputs(region: str, outputs: dict[str, pd.DataFrame]) -> dict[str, Path]:
    out_dir = repo_path("data", "intermediate", "lightcast_io_shares")
    out_dir.mkdir(parents=True, exist_ok=True)

    name_prefix = {
        "core": "lightcast_core_auto",
        "supply_chain": "lightcast_supply_chain",
        "weighted": "lightcast_weighted_supply_chain",
    }

    paths: dict[str, Path] = {}
    for key, df in outputs.items():
        prefix = name_prefix.get(key, f"lightcast_{key}")
        filename = f"{prefix}_{region}.csv"
        path = out_dir / filename
        df.to_csv(path, index=False)
        paths[key] = path
        print(f"Wrote {key} attribution for {region.upper()} to {path}")
    return paths


def update_comparison_tables() -> None:
    comparison_script = repo_path("scripts", "build_auto_share_comparison.py")
    plot_script = repo_path("scripts", "plot_auto_share_comparison.py")

    print("Updating comparative table...")
    try:
        runpy.run_path(str(comparison_script), run_name="__main__")
    except PermissionError as exc:
        print(
            f"Unable to update comparison table ({comparison_script}). "
            "Ensure the CSV is not open in another application and rerun. "
            f"Original error: {exc}"
        )
        raise

    print("Updating comparison plot...")
    runpy.run_path(str(plot_script), run_name="__main__")


def main() -> None:
    employment_path = repo_path("data", "raw", "emp_2024_10.csv")
    matrices = {
        "mi": repo_path("data", "raw", "mi_regional_matrix_cleaned_industries.csv"),
        "us": repo_path("data", "raw", "us_regional_matrix_cleaned_industries.csv"),
    }

    employment = load_employment(employment_path)
    generated_paths: dict[str, dict[str, Path]] = {}

    for region, matrix_path in matrices.items():
        if not matrix_path.exists():
            print(f"Skipping {region.upper()} - missing matrix: {matrix_path}")
            continue
        outputs = compute_region_outputs(matrix_path, employment)
        generated_paths[region] = write_outputs(region, outputs)

    if generated_paths:
        update_comparison_tables()
    else:
        print("No attribution outputs generated; comparison table not updated.")


if __name__ == "__main__":
    main()
