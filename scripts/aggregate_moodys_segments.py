import pandas as pd
from pathlib import Path

SEGMENT_LOOKUP_PATH = Path("data/lookups/segment_assignments.csv")
MI_METRICS_PATH = Path("data/interim/moodys_michigan_2024_2030.csv")
US_METRICS_PATH = Path("data/interim/moodys_us_2024_2030.csv")
OUTPUTS = {
    "segments": {
        "mi": Path("data/interim/moodys_michigan_segments_2024_2030.csv"),
        "us": Path("data/interim/moodys_us_segments_2024_2030.csv"),
        "group_cols": ["segment_id", "segment_canonical_name"],
        "rename_map": {"segment_canonical_name": "segment_name"},
        "sort_order": None,
    },
    "stages": {
        "mi": Path("data/interim/moodys_michigan_stages_2024_2030.csv"),
        "us": Path("data/interim/moodys_us_stages_2024_2030.csv"),
        "group_cols": ["stage"],
        "rename_map": {},
        "sort_order": {
            "column": "stage",
            "order": ["Upstream", "OEM", "Downstream"],
        },
    },
}

METRIC_KEYS = ["employment", "wages", "gdp"]
BASE_YEAR = 2024
TARGET_YEAR = 2030
NAICS_OVERRIDES = {"4471": "4571"}


def load_segment_lookup() -> pd.DataFrame:
    lookup = pd.read_csv(SEGMENT_LOOKUP_PATH, dtype={"naics_code": str})
    required_cols = {"naics_code", "segment_id", "segment_name", "stage"}
    missing = required_cols - set(lookup.columns)
    if missing:
        raise KeyError(f"Missing required columns in segment lookup: {missing}")
    lookup["segment_id"] = lookup["segment_id"].astype(int)
    lookup["segment_canonical_name"] = lookup["segment_name"].str.split(" - ").str[0].str.strip()
    return lookup[["naics_code", "segment_id", "segment_canonical_name", "stage"]]


def harmonize_naics(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if NAICS_OVERRIDES:
        df["naics_code"] = df["naics_code"].replace(NAICS_OVERRIDES)
    df = df.drop_duplicates(subset=["naics_code"])
    return df


def aggregate_by_group(metrics_df: pd.DataFrame, segment_lookup: pd.DataFrame, group_cols: list[str], rename_map: dict[str, str], sort_order: dict | None) -> pd.DataFrame:
    df = harmonize_naics(metrics_df)
    df = df.merge(segment_lookup, on="naics_code", how="left", validate="many_to_one")
    if df[group_cols].isna().any().any():
        missing_codes = sorted(df.loc[df[group_cols].isna().any(axis=1), "naics_code"].unique())
        raise ValueError(f"Segment mapping missing for NAICS codes: {missing_codes}")

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

    grouped = grouped.rename(columns=rename_map)

    sort_cols = [rename_map.get(col, col) for col in group_cols]
    if sort_order and sort_order.get("column") in grouped.columns:
        col = sort_order["column"]
        order = sort_order.get("order")
        grouped[col] = pd.Categorical(grouped[col], categories=order, ordered=True)
        grouped = grouped.sort_values(col)
    else:
        grouped = grouped.sort_values(sort_cols)

    grouped = grouped.reset_index(drop=True)
    return grouped


def main():
    segment_lookup = load_segment_lookup()
    mi_metrics = pd.read_csv(MI_METRICS_PATH, dtype={"naics_code": str})
    us_metrics = pd.read_csv(US_METRICS_PATH, dtype={"naics_code": str})

    for config in OUTPUTS.values():
        group_cols = config["group_cols"]
        rename_map = config["rename_map"]
        sort_order = config["sort_order"]

        mi_grouped = aggregate_by_group(mi_metrics, segment_lookup, group_cols, rename_map, sort_order)
        us_grouped = aggregate_by_group(us_metrics, segment_lookup, group_cols, rename_map, sort_order)

        mi_grouped.to_csv(config["mi"], index=False)
        us_grouped.to_csv(config["us"], index=False)


if __name__ == "__main__":
    main()
