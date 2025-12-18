"""Summarize occupation employment change by education and education+training (2021-2024 and 2024-2030).

This refreshes the original education-change script for the 2024 annual dashboard
outputs and adds a custom education+training recode:

1) BA+ - education is Bachelor's degree or higher
2) Associate's - education is Associate's
3) HS/SC + moderate/long OJT - education not in (1)/(2) and training is moderate/long OJT, internship, or apprenticeship
4) HS/SC + no significant OJT - education not in (1)/(2) and training not in the moderate/long set
5) Other - fallback (should be empty)

Outputs include both the auto-adjusted 2024-2030 change and the raw 2021-2024 change,
saved under `data/processed/sam_auto_dashboard_2024_refresh/occ_change_by_education/`.
"""


from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd


AUTO_BASE_YEAR = 2024
AUTO_TARGET_YEAR = 2030
RAW_BASE_YEAR = 2021
RAW_TARGET_YEAR = 2024
METHODOLOGY_FILTER = "sam_mi_moodys_mi"
PROJECTION_METHOD_FILTER = "moodys_mi"

SEGMENT_FILE = Path("data/processed/sam_auto_dashboard_2024_refresh/sam_occ_segment_totals_2024_2034.csv")
SEGMENT_TIMESERIES_FILE = Path("data/processed/sam_auto_dashboard_2024_refresh/sam_employment_segment_timeseries.csv")
OUTPUT_DIR = Path("data/processed/sam_auto_dashboard_2024_refresh/occ_change_by_education")

STAGE_GROUPS = [
    {"key": "upstream", "name": "Upstream", "label": "Upstream (segments 1-6)", "segments": set(range(1, 7))},
    {"key": "core_auto", "name": "Core Automotive", "label": "Core Automotive (segment 7)", "segments": {7}},
    {"key": "downstream", "name": "Downstream", "label": "Downstream (segments 8-10)", "segments": {8, 9, 10}},
    {"key": "upstream_core", "name": "Upstream + Core Automotive", "label": "Upstream + Core Automotive (segments 1-7)", "segments": set(range(1, 8))},
    {"key": "all_segments", "name": "All Segments", "label": "All Segments (segments 1-10)", "segments": set(range(1, 11))},
]

MODERATE_LONG_TRAINING = {
    "moderate-term on-the-job training",
    "long-term on-the-job training",
    "internship/residency",
    "apprenticeship",
}


def normalize_education(value: str | float | int | None) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "Unreported"
    text = str(value).strip().lower()
    if not text or text in {"nan", "none"}:
        return "Unreported"
    if "sc" in text or "associate" in text or "postsecondary" in text:
        return "SC or Associate's"
    if "hs" in text or "high school" in text:
        return "HS or Less"
    return "BA+"


def normalize_training(value: str | float | int | None) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ""
    return str(value).strip().lower()


def classify_custom_edu_training(row: pd.Series) -> str:
    # Primary education source: entry education if available, else grouped.
    edu_raw = str(row.get("ep_entry_education", "")).strip().lower()
    edu_grouped = normalize_education(row.get("ep_edu_grouped"))

    if any(token in edu_raw for token in ["bachelor", "master", "doctoral", "doctor", "professional", "ph.d", "phd"]):
        edu_class = "BA+"
    elif "associate" in edu_raw:
        edu_class = "Associate's"
    elif edu_grouped == "BA+":
        edu_class = "BA+"
    elif edu_grouped == "SC or Associate's":
        # If grouped is SC/Associate but raw text mentions associate, catch above; otherwise treat as non-associate.
        edu_class = "SC/HS"
    else:
        edu_class = "SC/HS"

    if edu_class == "BA+":
        return "BA+"
    if edu_class == "Associate's":
        return "Associate's"

    training_raw = row.get("ep_on_the_job_training")
    training_text = normalize_training(training_raw)
    if not training_text:
        training_text = normalize_training(row.get("ep_edu_training_grouped"))
    if training_text in MODERATE_LONG_TRAINING:
        return "HS/SC + moderate/long OJT"
    if training_text:
        return "HS/SC + no significant OJT"
    return "Other"


def load_segment_panel(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Cannot locate {path}")
    df = pd.read_csv(path)
    years_needed = {AUTO_BASE_YEAR, AUTO_TARGET_YEAR, RAW_TARGET_YEAR}
    df = df[
        (df["year"].isin(years_needed))
        & (df["methodology"] == METHODOLOGY_FILTER)
        & (df["projection_method"] == PROJECTION_METHOD_FILTER)
    ].copy()
    if df.empty:
        raise ValueError("No rows left after filtering for Moody's MI scenario.")
    df["segment_id"] = pd.to_numeric(df["segment_id"], errors="coerce").astype("Int64")
    df = df.dropna(subset=["segment_id"])
    df["segment_id"] = df["segment_id"].astype(int)
    df = df[df["segment_id"] > 0]

    df["education_group"] = df["ep_edu_grouped"].apply(normalize_education)
    training_source = df.get("ep_edu_training_grouped")
    if training_source is not None:
        df["training_group"] = (
            training_source.fillna("Unreported")
            .astype(str)
            .str.strip()
            .replace("", "Unreported")
        )
    else:
        df["training_group"] = df["education_group"]
    df["custom_training_group"] = df.apply(classify_custom_edu_training, axis=1)
    return df


def aggregate_segment_year_totals(df: pd.DataFrame, value_col: str) -> pd.DataFrame:
    group_cols = [
        "methodology",
        "projection_method",
        "projection_label",
        "segment_id",
        "segment_name",
        "education_group",
        "year",
    ]
    grouped = df.groupby(group_cols, as_index=False)[value_col].sum()
    return grouped.rename(columns={value_col: "employment"})


def load_segment_auto_shares(year: int) -> tuple[dict[int, float], dict[int, float]]:
    if not SEGMENT_TIMESERIES_FILE.exists():
        raise FileNotFoundError(SEGMENT_TIMESERIES_FILE)
    seg = pd.read_csv(SEGMENT_TIMESERIES_FILE)
    seg = seg[(seg["year"] == year) & seg["segment_id"].notna()].copy()
    if seg.empty:
        raise ValueError(f"Segment time series missing year {year} data")
    seg["segment_id"] = seg["segment_id"].astype(int)
    seg["share_ratio"] = np.where(
        seg["employment_raw"].fillna(0.0) > 0,
        seg["employment_auto"].fillna(0.0) / seg["employment_raw"].replace(0, np.nan),
        1.0,
    )
    seg["share_ratio"] = seg["share_ratio"].replace([np.inf, -np.inf], np.nan).fillna(1.0)
    share_map = seg.set_index("segment_id")["share_ratio"].to_dict()
    auto_totals = seg.set_index("segment_id")["employment_auto"].to_dict()
    return share_map, auto_totals


def build_raw_and_auto_baseline_panels(
    df: pd.DataFrame,
    auto_share_lookup: dict[int, float],
    auto_segment_totals: dict[int, float],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    snapshot = df[df["year"] == RAW_TARGET_YEAR].copy()
    if snapshot.empty:
        raise ValueError("Unable to locate 2024 rows for raw comparison.")

    valid_mask = snapshot["employment_raw"].fillna(0.0) > 0.0
    snapshot = snapshot[valid_mask].copy()
    if snapshot.empty:
        raise ValueError("No occupations remain with 2024 employment data.")

    snapshot["share_ratio"] = snapshot["segment_id"].map(auto_share_lookup).fillna(1.0)
    snapshot["empl_2021_auto"] = snapshot["empl_2021"].fillna(0.0) * snapshot["share_ratio"]

    # Adjust 2021 auto totals to match 2024 auto totals within each segment.
    for seg_id, seg_df in snapshot.groupby("segment_id"):
        target = auto_segment_totals.get(seg_id)
        if target is None:
            continue
        current = seg_df["empl_2021_auto"].sum()
        residual = target - current
        if abs(residual) <= 1e-6:
            continue
        weights = seg_df["employment_auto"].fillna(0.0)
        total_weights = weights.sum()
        if total_weights <= 0:
            continue
        adjustment = residual * (weights / total_weights)
        snapshot.loc[seg_df.index, "empl_2021_auto"] += adjustment

    raw_base = (
        snapshot.groupby(
            [
                "methodology",
                "projection_method",
                "projection_label",
                "segment_id",
                "segment_name",
                "education_group",
            ]
        )["empl_2021"]
        .sum()
        .reset_index()
    )
    raw_base["year"] = RAW_BASE_YEAR
    raw_base.rename(columns={"empl_2021": "employment"}, inplace=True)

    raw_target = snapshot.groupby(
        [
            "methodology",
            "projection_method",
            "projection_label",
            "segment_id",
            "segment_name",
            "education_group",
            "year",
        ],
        as_index=False,
    )["employment_raw"].sum()
    raw_target.rename(columns={"employment_raw": "employment"}, inplace=True)

    raw_panel = pd.concat([raw_base, raw_target], ignore_index=True, sort=False)

    auto_base = (
        snapshot.groupby(
            [
                "methodology",
                "projection_method",
                "projection_label",
                "segment_id",
                "segment_name",
                "education_group",
            ]
        )["empl_2021_auto"]
        .sum()
        .reset_index()
    )
    auto_base["year"] = RAW_BASE_YEAR
    auto_base.rename(columns={"empl_2021_auto": "employment"}, inplace=True)

    auto_target = snapshot.groupby(
        [
            "methodology",
            "projection_method",
            "projection_label",
            "segment_id",
            "segment_name",
            "education_group",
            "year",
        ],
        as_index=False,
    )["employment_auto"].sum()
    auto_target.rename(columns={"employment_auto": "employment"}, inplace=True)

    auto_panel = pd.concat([auto_base, auto_target], ignore_index=True, sort=False)

    return raw_panel, auto_panel


def build_stage_panel(segment_panel: pd.DataFrame) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for group in STAGE_GROUPS:
        mask = segment_panel["segment_id"].isin(group["segments"])
        subset = segment_panel[mask]
        if subset.empty:
            continue
        agg = (
            subset.groupby(
                [
                    "methodology",
                    "projection_method",
                    "projection_label",
                    "education_group",
                    "year",
                ],
                as_index=False,
            )["employment"].sum()
        )
        agg["stage_key"] = group["key"]
        agg["stage_name"] = group["name"]
        agg["stage_label"] = group["label"]
        frames.append(agg)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def compute_change_table(
    df: pd.DataFrame,
    group_cols: list[str],
    base_year: int,
    target_year: int,
) -> pd.DataFrame:
    base = (
        df[df["year"] == base_year]
        .drop(columns="year")
        .rename(columns={"employment": "employment_base"})
    )
    target = (
        df[df["year"] == target_year]
        .drop(columns="year")
        .rename(columns={"employment": "employment_target"})
    )
    merged = base.merge(target, on=group_cols, how="outer").fillna(0.0)
    merged["employment_change"] = merged["employment_target"] - merged["employment_base"]
    merged["pct_change"] = np.where(
        merged["employment_base"] != 0,
        merged["employment_change"] / merged["employment_base"],
        np.nan,
    )
    return merged


def add_shares(df: pd.DataFrame, group_for_total: list[str]) -> pd.DataFrame:
    """Compute base/target shares within the provided grouping (e.g., within segment or stage)."""
    if df.empty:
        return df
    df = df.copy()
    for col in ["employment_base", "employment_target"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    totals_base = df.groupby(group_for_total)["employment_base"].transform("sum")
    totals_target = df.groupby(group_for_total)["employment_target"].transform("sum")
    df["share_base"] = np.where(totals_base != 0, df["employment_base"] / totals_base, np.nan)
    df["share_target"] = np.where(totals_target != 0, df["employment_target"] / totals_target, np.nan)
    return df


def add_change_share(df: pd.DataFrame, group_for_total: list[str]) -> pd.DataFrame:
    """Compute share of employment_change within the provided grouping."""
    if df.empty or "employment_change" not in df.columns:
        return df
    df = df.copy()
    change_total = df.groupby(group_for_total)["employment_change"].transform("sum")
    df["share_change"] = np.where(change_total != 0, df["employment_change"] / change_total, np.nan)
    return df


def sort_education(df: pd.DataFrame, col: str, order: list[str], extra_keys: list[str] | None = None) -> pd.DataFrame:
    if df.empty or col not in df.columns:
        return df
    categories = pd.Categorical(df[col], categories=order, ordered=True)
    df[col] = categories
    sort_cols = (extra_keys or []) + [col]
    existing = [c for c in sort_cols if c in df.columns]
    return df.sort_values(existing, kind="mergesort")


def build_group_tables(
    df: pd.DataFrame,
    auto_share_lookup: dict[int, float],
    auto_segment_totals: dict[int, float],
) -> dict[str, pd.DataFrame]:
    tables: dict[str, pd.DataFrame] = {}

    segment_panel = aggregate_segment_year_totals(df, "employment_auto")
    stage_panel = build_stage_panel(segment_panel)

    segment_group_cols = [
        "methodology",
        "projection_method",
        "projection_label",
        "segment_id",
        "segment_name",
        "education_group",
    ]
    stage_group_cols = [
        "methodology",
        "projection_method",
        "projection_label",
        "stage_key",
        "stage_name",
        "stage_label",
        "education_group",
    ]

    tables["segment_auto"] = compute_change_table(
        segment_panel,
        segment_group_cols,
        AUTO_BASE_YEAR,
        AUTO_TARGET_YEAR,
    )
    tables["stage_auto"] = compute_change_table(
        stage_panel,
        stage_group_cols,
        AUTO_BASE_YEAR,
        AUTO_TARGET_YEAR,
    )
    tables["total_auto"] = tables["stage_auto"][tables["stage_auto"]["stage_key"] == "all_segments"].copy()

    raw_segment_panel, auto_baseline_panel = build_raw_and_auto_baseline_panels(
        df, auto_share_lookup, auto_segment_totals
    )
    raw_stage_panel = build_stage_panel(raw_segment_panel)
    auto_baseline_stage_panel = build_stage_panel(auto_baseline_panel)

    tables["segment_raw"] = compute_change_table(
        raw_segment_panel,
        segment_group_cols,
        RAW_BASE_YEAR,
        RAW_TARGET_YEAR,
    )
    tables["stage_raw"] = compute_change_table(
        raw_stage_panel,
        stage_group_cols,
        RAW_BASE_YEAR,
        RAW_TARGET_YEAR,
    )
    tables["total_raw"] = tables["stage_raw"][tables["stage_raw"]["stage_key"] == "all_segments"].copy()

    tables["segment_auto_baseline"] = compute_change_table(
        auto_baseline_panel,
        segment_group_cols,
        RAW_BASE_YEAR,
        RAW_TARGET_YEAR,
    )
    tables["stage_auto_baseline"] = compute_change_table(
        auto_baseline_stage_panel,
        stage_group_cols,
        RAW_BASE_YEAR,
        RAW_TARGET_YEAR,
    )
    tables["total_auto_baseline"] = tables["stage_auto_baseline"][
        tables["stage_auto_baseline"]["stage_key"] == "all_segments"
    ].copy()

    # Add within-group shares (segment/stage), skip totals which represent 100%.
    seg_share_keys = ["methodology", "projection_method", "projection_label", "segment_id", "segment_name"]
    stage_share_keys = ["methodology", "projection_method", "projection_label", "stage_key", "stage_name", "stage_label"]
    for key in [
        "segment_auto",
        "segment_raw",
        "segment_auto_baseline",
    ]:
        tables[key] = add_shares(tables[key], seg_share_keys)
        tables[key] = add_change_share(tables[key], seg_share_keys)
    for key in [
        "stage_auto",
        "stage_raw",
        "stage_auto_baseline",
    ]:
        tables[key] = add_shares(tables[key], stage_share_keys)
        tables[key] = add_change_share(tables[key], stage_share_keys)

    return tables


def main() -> None:
    segment_df = load_segment_panel(SEGMENT_FILE)
    share_map, auto_totals = load_segment_auto_shares(RAW_BASE_YEAR)

    training_df = segment_df.copy()
    training_df["education_group"] = training_df["training_group"]

    custom_df = segment_df.copy()
    custom_df["education_group"] = custom_df["custom_training_group"]

    group_configs = [
        ("Education", segment_df),
        ("Education+Training", training_df),
        ("Edu+Training Custom", custom_df),
    ]

    results: dict[str, dict[str, pd.DataFrame]] = {}
    for label, df in group_configs:
        results[label] = build_group_tables(df, share_map, auto_totals)

    # Apply ordering by education/training group
    edu_order = ["BA+", "SC or Associate's", "HS or Less", "Unreported", "Other"]
    training_order = [
        "BA+",
        "SC/Associate or Employer Training",
        "HS or Less - Limited Training",
        "Unreported",
        "Other",
    ]
    custom_order = [
        "BA+",
        "Associate's",
        "HS/SC + moderate/long OJT",
        "HS/SC + no significant OJT",
        "Other",
        "Unreported",
    ]
    sort_keys_segment = ["segment_id"]
    sort_keys_stage = ["stage_key"]

    def apply_orders(res_dict: dict[str, pd.DataFrame], order: list[str]) -> dict[str, pd.DataFrame]:
        out = {}
        for k, v in res_dict.items():
            if k.startswith("segment_"):
                out[k] = sort_education(v, "education_group", order, extra_keys=sort_keys_segment)
            elif k.startswith("stage_"):
                out[k] = sort_education(v, "education_group", order, extra_keys=sort_keys_stage)
            else:
                out[k] = v
        return out

    results["Education"] = apply_orders(results["Education"], edu_order)
    results["Education+Training"] = apply_orders(results["Education+Training"], training_order)
    results["Edu+Training Custom"] = apply_orders(results["Edu+Training Custom"], custom_order)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_specs = [
        ("segment_occ_change_by_education_2024_2030", "segment_auto"),
        ("stage_occ_change_by_education_2024_2030", "stage_auto"),
        ("total_occ_change_by_education_2024_2030", "total_auto"),
        ("segment_occ_change_by_education_2021_2024_raw", "segment_raw"),
        ("stage_occ_change_by_education_2021_2024_raw", "stage_raw"),
        ("total_occ_change_by_education_2021_2024_raw", "total_raw"),
        ("segment_occ_change_by_education_2021_2024_auto", "segment_auto_baseline"),
        ("stage_occ_change_by_education_2021_2024_auto", "stage_auto_baseline"),
        ("total_occ_change_by_education_2021_2024_auto", "total_auto_baseline"),
    ]

    for filename, key in output_specs:
        edu_df = results["Education"][key]
        excel_path = OUTPUT_DIR / f"{filename}.xlsx"
        with pd.ExcelWriter(excel_path) as writer:
            edu_df.to_excel(writer, sheet_name="Education", index=False)
            training_sheet = results.get("Education+Training", {}).get(key)
            if training_sheet is not None:
                training_sheet.to_excel(writer, sheet_name="Education+Training", index=False)
            custom_sheet = results.get("Edu+Training Custom", {}).get(key)
            if custom_sheet is not None:
                custom_sheet.to_excel(writer, sheet_name="Edu+Training (custom)", index=False)

    print("Saved education-change tables to", OUTPUT_DIR)


if __name__ == "__main__":
    main()
