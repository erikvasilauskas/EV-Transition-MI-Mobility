import pandas as pd
from pathlib import Path

SEGMENT_LOOKUP_PATH = Path("data/lookups/segment_assignments.csv")
MI_METRICS_PATH = Path("data/interim/moodys_michigan_2024_2030.csv")
US_METRICS_PATH = Path("data/interim/moodys_us_2024_2030.csv")
OUTPUT_MI = Path("data/interim/moodys_michigan_segments_2024_2030.csv")
OUTPUT_US = Path("data/interim/moodys_us_segments_2024_2030.csv")

METRIC_KEYS = ["employment", "wages", "gdp"]
BASE_YEAR = 2024
TARGET_YEAR = 2030
NAICS_OVERRIDES = {"4471": "4571"}


def load_segment_lookup():
    lookup = pd.read_csv(SEGMENT_LOOKUP_PATH, dtype={"naics_code": str})
    required_cols = {"naics_code", "segment_id", "segment_name"}
    missing = required_cols - set(lookup.columns)
    if missing:
        raise KeyError(f"Missing required columns in segment lookup: {missing}")
    lookup["segment_id"] = lookup["segment_id"].astype(int)
    lookup["segment_canonical_name"] = lookup["segment_name"].str.split(" - ").str[0].str.strip()
    return lookup[["naics_code", "segment_id", "segment_canonical_name"]]


def harmonize_naics(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if NAICS_OVERRIDES:
        df["naics_code"] = df["naics_code"].replace(NAICS_OVERRIDES)
    df = df.drop_duplicates(subset=["naics_code"])
    return df


def aggregate_by_segment(metrics_df: pd.DataFrame, segment_lookup: pd.DataFrame) -> pd.DataFrame:
    df = harmonize_naics(metrics_df)
    df = df.merge(segment_lookup, on="naics_code", how="left", validate="many_to_one")
    if df["segment_id"].isna().any():
        missing_codes = sorted(df.loc[df["segment_id"].isna(), "naics_code"].unique())
        raise ValueError(f"Segment mapping missing for NAICS codes: {missing_codes}")

    group_cols = ["segment_id", "segment_canonical_name"]
    value_cols = []
    for metric in METRIC_KEYS:
        value_cols.append(f"{BASE_YEAR}_{metric}")
        value_cols.append(f"{TARGET_YEAR}_{metric}")

    grouped = df.groupby(group_cols, as_index=False)[value_cols].sum()

    for metric in METRIC_KEYS:
        base_col = f"{BASE_YEAR}_{metric}"
        target_col = f"{TARGET_YEAR}_{metric}"
        pct_col = f"pct_change_{metric}_{BASE_YEAR}_{TARGET_YEAR}"
        grouped[pct_col] = (grouped[target_col] - grouped[base_col]) / grouped[base_col].replace({0: pd.NA}) * 100
        grouped.loc[grouped[base_col] == 0, pct_col] = pd.NA

    grouped = grouped.rename(columns={"segment_canonical_name": "segment_name"})
    grouped = grouped.sort_values("segment_id").reset_index(drop=True)

    return grouped


def main():
    segment_lookup = load_segment_lookup()
    mi_metrics = pd.read_csv(MI_METRICS_PATH, dtype={"naics_code": str})
    us_metrics = pd.read_csv(US_METRICS_PATH, dtype={"naics_code": str})

    mi_by_segment = aggregate_by_segment(mi_metrics, segment_lookup)
    us_by_segment = aggregate_by_segment(us_metrics, segment_lookup)

    mi_by_segment.to_csv(OUTPUT_MI, index=False)
    us_by_segment.to_csv(OUTPUT_US, index=False)


if __name__ == "__main__":
    main()
