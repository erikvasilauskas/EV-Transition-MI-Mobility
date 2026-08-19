"""Merge occupational AI-exposure measures with SAM/Moody's MI employment.

The analysis deliberately uses exact 2018 SOC matches only. Aggregate or hybrid
employment codes are retained in the merged data with missing exposure fields;
they are never silently dropped or imputed.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "outputs"
METHODOLOGY = "sam_mi_moodys_mi"
BASE_YEAR = 2024
TARGET_YEAR = 2030
QUARTILES = ["q1", "q2", "q3", "q4"]  # q1 is highest exposure
ASSEMBLER_SOURCE_SOC = "51-2090"
TEAM_ASSEMBLER_SOC = "51-2092"
TEAM_ASSEMBLER_WEIGHT = 0.83
RESIDUAL_ASSEMBLER_WEIGHT = 0.17
ASSEMBLER_IMPUTATION_METHOD = "bls_83pct_team_assembler_17pct_51_20xx_donor_median"


def normalize_soc(series: pd.Series) -> pd.Series:
    return series.astype("string").str.strip()


def load_exposure() -> pd.DataFrame:
    path = ROOT / "exposure_index_soc_2018_bls_nem_titles.xlsx"
    exposure = pd.read_excel(path, sheet_name="Composite exposure index")
    exposure = exposure.rename(
        columns={
            "SOC_2018": "exposure_soc_2018",
            "Occupation title": "exposure_occupation_title",
            "Exposure score": "exposure_score",
            "Exposure score, percentile": "exposure_percentile",
            "Exposure quartile": "exposure_quartile",
        }
    )
    exposure["exposure_soc_2018"] = normalize_soc(exposure["exposure_soc_2018"])
    if exposure["exposure_soc_2018"].duplicated().any():
        raise ValueError("Exposure index contains duplicate SOC codes.")
    observed = set(exposure["exposure_quartile"].dropna().astype(str))
    if observed != set(QUARTILES):
        raise ValueError(f"Unexpected exposure quartiles: {sorted(observed)}")
    q1_mean = exposure.loc[exposure["exposure_quartile"].eq("q1"), "exposure_score"].mean()
    q4_mean = exposure.loc[exposure["exposure_quartile"].eq("q4"), "exposure_score"].mean()
    if not q1_mean > q4_mean:
        raise ValueError("Expected q1 to represent the highest-exposure quartile.")
    return exposure


def load_bls_crosswalk() -> pd.DataFrame:
    path = ROOT / "bls_table3_taxonomy_crosswalk.csv"
    crosswalk = pd.read_csv(
        path,
        dtype={"source_ep_oews_code": str, "target_soc_2018": str},
    )
    crosswalk["source_ep_oews_code"] = normalize_soc(crosswalk["source_ep_oews_code"])
    crosswalk["target_soc_2018"] = normalize_soc(crosswalk["target_soc_2018"])
    crosswalk["final_weight"] = pd.to_numeric(crosswalk["final_weight"], errors="raise")
    return crosswalk


def percentile_from_reference(score: float, exposure: pd.DataFrame) -> float:
    reference = exposure[["exposure_score", "exposure_percentile"]].dropna().sort_values("exposure_score")
    return float(np.interp(score, reference["exposure_score"], reference["exposure_percentile"]))


def quartile_from_percentile(percentile: float) -> str:
    return "q1" if percentile >= 75 else "q2" if percentile >= 50 else "q3" if percentile >= 25 else "q4"


def build_complete_crosswalk_estimates(
    exposure: pd.DataFrame, crosswalk: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    component_audit = crosswalk.merge(
        exposure[
            [
                "exposure_soc_2018",
                "exposure_score",
                "exposure_percentile",
                "exposure_quartile",
            ]
        ],
        how="left",
        left_on="target_soc_2018",
        right_on="exposure_soc_2018",
        validate="many_to_one",
    )
    component_audit["target_has_exposure"] = component_audit["exposure_score"].notna()

    estimates: list[dict[str, object]] = []
    for (source_soc, source_title), group in component_audit.groupby(
        ["source_ep_oews_code", "source_ep_oews_title"], sort=True
    ):
        weight_sum = float(group["final_weight"].sum())
        weight_with_exposure = float(group.loc[group["target_has_exposure"], "final_weight"].sum())
        fully_covered = bool(group["target_has_exposure"].all())
        applied = fully_covered and source_soc != ASSEMBLER_SOURCE_SOC
        score = np.nan
        percentile = np.nan
        quartile: object = pd.NA
        if applied:
            score = float(np.average(group["exposure_score"], weights=group["final_weight"]))
            percentile = percentile_from_reference(score, exposure)
            quartile = quartile_from_percentile(percentile)
        estimates.append(
            {
                "source_soc": source_soc,
                "source_title": source_title,
                "component_count": len(group),
                "published_weight_sum": weight_sum,
                "weight_with_exposure": weight_with_exposure,
                "fully_covered_by_exposure_index": fully_covered,
                "applied_as_complete_crosswalk": applied,
                "exposure_score": score,
                "exposure_percentile": percentile,
                "exposure_quartile": quartile,
                "mapping_method": "bls_table3_complete_weighted_crosswalk" if applied else pd.NA,
            }
        )
    return pd.DataFrame(estimates), component_audit


def build_assembler_imputation(exposure: pd.DataFrame) -> dict[str, object]:
    team = exposure.loc[exposure["exposure_soc_2018"].eq(TEAM_ASSEMBLER_SOC)]
    if len(team) != 1:
        raise ValueError(f"Expected one exposure record for {TEAM_ASSEMBLER_SOC}; found {len(team)}")
    team_score = float(team["exposure_score"].iloc[0])

    donor_mask = exposure["exposure_soc_2018"].str.startswith("51-20", na=False) & ~exposure[
        "exposure_soc_2018"
    ].eq(TEAM_ASSEMBLER_SOC)
    donor_scores = exposure.loc[donor_mask, "exposure_score"].dropna()
    if donor_scores.empty:
        raise ValueError("No comparable 51-20xx residual donor occupations found.")

    residual_low = float(donor_scores.min())
    residual_central = float(donor_scores.median())
    residual_high = float(donor_scores.max())

    def composite(residual_score: float) -> float:
        return TEAM_ASSEMBLER_WEIGHT * team_score + RESIDUAL_ASSEMBLER_WEIGHT * residual_score

    score_low = composite(residual_low)
    score_central = composite(residual_central)
    score_high = composite(residual_high)
    percentile_low = percentile_from_reference(score_low, exposure)
    percentile_central = percentile_from_reference(score_central, exposure)
    percentile_high = percentile_from_reference(score_high, exposure)
    quartile = quartile_from_percentile(percentile_central)

    return {
        "source_soc": ASSEMBLER_SOURCE_SOC,
        "source_title": "Miscellaneous Assemblers and Fabricators",
        "team_assembler_soc": TEAM_ASSEMBLER_SOC,
        "team_assembler_weight": TEAM_ASSEMBLER_WEIGHT,
        "team_assembler_score": team_score,
        "residual_weight": RESIDUAL_ASSEMBLER_WEIGHT,
        "residual_donor_definition": "Other exposure-index occupations with SOC codes beginning 51-20",
        "residual_donor_count": int(donor_scores.size),
        "residual_score_low": residual_low,
        "residual_score_central": residual_central,
        "residual_score_high": residual_high,
        "exposure_score_low": score_low,
        "exposure_score_central": score_central,
        "exposure_score_high": score_high,
        "exposure_percentile_low": percentile_low,
        "exposure_percentile_central": percentile_central,
        "exposure_percentile_high": percentile_high,
        "exposure_quartile": quartile,
        "imputation_method": ASSEMBLER_IMPUTATION_METHOD,
    }


def merge_exposure(
    frame: pd.DataFrame,
    exposure: pd.DataFrame,
    crosswalk_estimates: pd.DataFrame,
) -> pd.DataFrame:
    out = frame.copy()
    out["occcd"] = normalize_soc(out["occcd"])
    out = out.merge(
        exposure,
        how="left",
        left_on="occcd",
        right_on="exposure_soc_2018",
        validate="many_to_one",
    )
    out["exposure_exact_match"] = out["exposure_score"].notna()
    out["exposure_crosswalked"] = False
    out["exposure_mapping_method"] = pd.NA
    out["exposure_imputed"] = False
    out["exposure_imputation_method"] = pd.NA
    out["exposure_score_lower"] = out["exposure_score"]
    out["exposure_score_upper"] = out["exposure_score"]
    out["exposure_percentile_lower"] = out["exposure_percentile"]
    out["exposure_percentile_upper"] = out["exposure_percentile"]

    complete = crosswalk_estimates.loc[crosswalk_estimates["applied_as_complete_crosswalk"]]
    for row in complete.itertuples(index=False):
        mask = out["occcd"].eq(row.source_soc) & ~out["exposure_exact_match"]
        out.loc[mask, "exposure_occupation_title"] = row.source_title
        out.loc[mask, "exposure_score"] = row.exposure_score
        out.loc[mask, "exposure_percentile"] = row.exposure_percentile
        out.loc[mask, "exposure_quartile"] = row.exposure_quartile
        out.loc[mask, "exposure_crosswalked"] = True
        out.loc[mask, "exposure_mapping_method"] = row.mapping_method
        out.loc[mask, "exposure_score_lower"] = row.exposure_score
        out.loc[mask, "exposure_score_upper"] = row.exposure_score
        out.loc[mask, "exposure_percentile_lower"] = row.exposure_percentile
        out.loc[mask, "exposure_percentile_upper"] = row.exposure_percentile

    imputation = build_assembler_imputation(exposure)
    mask = out["occcd"].eq(ASSEMBLER_SOURCE_SOC) & ~out["exposure_exact_match"]
    out.loc[mask, "exposure_occupation_title"] = imputation["source_title"]
    out.loc[mask, "exposure_score"] = imputation["exposure_score_central"]
    out.loc[mask, "exposure_percentile"] = imputation["exposure_percentile_central"]
    out.loc[mask, "exposure_quartile"] = imputation["exposure_quartile"]
    out.loc[mask, "exposure_crosswalked"] = True
    out.loc[mask, "exposure_mapping_method"] = "bls_table3_weighted_crosswalk_with_residual_imputation"
    out.loc[mask, "exposure_imputed"] = True
    out.loc[mask, "exposure_imputation_method"] = imputation["imputation_method"]
    out.loc[mask, "exposure_score_lower"] = imputation["exposure_score_low"]
    out.loc[mask, "exposure_score_upper"] = imputation["exposure_score_high"]
    out.loc[mask, "exposure_percentile_lower"] = imputation["exposure_percentile_low"]
    out.loc[mask, "exposure_percentile_upper"] = imputation["exposure_percentile_high"]
    out["exposure_match"] = out["exposure_score"].notna()
    return out


def long_stage_employment(stage: pd.DataFrame) -> pd.DataFrame:
    id_cols = [
        "stage_clean",
        "methodology",
        "projection_method",
        "projection_label",
        "occcd",
        "soctitle",
        "exposure_soc_2018",
        "exposure_occupation_title",
        "exposure_score",
        "exposure_percentile",
        "exposure_quartile",
        "exposure_exact_match",
        "exposure_crosswalked",
        "exposure_mapping_method",
        "exposure_imputed",
        "exposure_imputation_method",
        "exposure_score_lower",
        "exposure_score_upper",
        "exposure_percentile_lower",
        "exposure_percentile_upper",
        "exposure_match",
    ]
    base = stage[id_cols + ["employment_auto_2024"]].rename(
        columns={"employment_auto_2024": "employment_auto"}
    )
    base["year"] = BASE_YEAR
    target = stage[id_cols + ["employment_auto"]].copy()
    target["year"] = TARGET_YEAR
    return pd.concat([base, target], ignore_index=True)


def summarize(frame: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    keys = group_cols + ["year"]
    for key, group in frame.groupby(keys, dropna=False, sort=True):
        if not isinstance(key, tuple):
            key = (key,)
        row = dict(zip(keys, key))
        employment = pd.to_numeric(group["employment_auto"], errors="coerce").fillna(0.0)
        matched = group["exposure_match"].fillna(False)
        matched_employment = employment.where(matched, 0.0)
        total = employment.sum()
        covered = matched_employment.sum()
        row["total_employment"] = total
        row["exposure_matched_employment"] = covered
        row["exposure_unmatched_employment"] = total - covered
        row["employment_coverage_pct"] = 100.0 * covered / total if total else np.nan

        if covered:
            row["employment_weighted_exposure_score"] = np.average(
                group.loc[matched, "exposure_score"], weights=employment.loc[matched]
            )
            row["employment_weighted_exposure_percentile"] = np.average(
                group.loc[matched, "exposure_percentile"], weights=employment.loc[matched]
            )
        else:
            row["employment_weighted_exposure_score"] = np.nan
            row["employment_weighted_exposure_percentile"] = np.nan

        for quartile in QUARTILES:
            q_emp = employment.where(group["exposure_quartile"].eq(quartile), 0.0).sum()
            row[f"{quartile}_employment"] = q_emp
            row[f"{quartile}_share_of_matched_pct"] = 100.0 * q_emp / covered if covered else np.nan
            row[f"{quartile}_share_of_total_pct"] = 100.0 * q_emp / total if total else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def change_table(summary: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    metrics = [
        "total_employment",
        "exposure_matched_employment",
        "employment_coverage_pct",
        "employment_weighted_exposure_score",
        "employment_weighted_exposure_percentile",
        "q1_employment",
        "q1_share_of_matched_pct",
        "q1_share_of_total_pct",
    ]
    base = summary.loc[summary["year"].eq(BASE_YEAR), group_cols + metrics].copy()
    target = summary.loc[summary["year"].eq(TARGET_YEAR), group_cols + metrics].copy()
    base = base.rename(columns={metric: f"{metric}_{BASE_YEAR}" for metric in metrics})
    target = target.rename(columns={metric: f"{metric}_{TARGET_YEAR}" for metric in metrics})
    out = base.merge(target, on=group_cols, how="outer", validate="one_to_one")
    out["total_employment_change"] = (
        out[f"total_employment_{TARGET_YEAR}"] - out[f"total_employment_{BASE_YEAR}"]
    )
    out["q1_employment_change"] = out[f"q1_employment_{TARGET_YEAR}"] - out[f"q1_employment_{BASE_YEAR}"]
    out["q1_employment_pct_change"] = np.where(
        out[f"q1_employment_{BASE_YEAR}"].ne(0),
        100.0 * out["q1_employment_change"] / out[f"q1_employment_{BASE_YEAR}"],
        np.nan,
    )
    return out


def unmatched_diagnostic(segment: pd.DataFrame) -> pd.DataFrame:
    # Use only mutually exclusive segments 1-10. Segment 0 is an all-segment
    # aggregate and segment 11 duplicates the upstream/core segments.
    subset = segment.loc[
        segment["year"].isin([BASE_YEAR, TARGET_YEAR])
        & segment["segment_id"].between(1, 10)
        & ~segment["exposure_match"]
    ].copy()
    diagnostic = (
        subset.groupby(["occcd", "soctitle", "year"], as_index=False)["employment_auto"]
        .sum()
        .pivot(index=["occcd", "soctitle"], columns="year", values="employment_auto")
        .reset_index()
        .rename(columns={BASE_YEAR: f"employment_{BASE_YEAR}", TARGET_YEAR: f"employment_{TARGET_YEAR}"})
    )
    for col in [f"employment_{BASE_YEAR}", f"employment_{TARGET_YEAR}"]:
        if col not in diagnostic:
            diagnostic[col] = 0.0
    diagnostic["employment_change"] = (
        diagnostic[f"employment_{TARGET_YEAR}"] - diagnostic[f"employment_{BASE_YEAR}"]
    )
    return diagnostic.sort_values(f"employment_{TARGET_YEAR}", ascending=False)


def plot_quartile_shares(
    summary: pd.DataFrame,
    group_col: str,
    label_col: str,
    year: int,
    title: str,
    output_name: str,
    x_label: str,
    exclude_segment_11: bool = False,
    show_data_labels: bool = False,
) -> None:
    data = summary.loc[summary["year"].eq(year)].copy()
    if exclude_segment_11:
        data = data.loc[data[group_col].between(1, 10)]
        data = data.sort_values(group_col)
    labels = data[label_col].astype(str).str.replace(r"^\d+\.\s*", "", regex=True)
    colors = {"q1": "#7a0019", "q2": "#d95f02", "q3": "#fdb863", "q4": "#5e81ac"}
    fig_height = max(3.2, 0.48 * len(data) + 1.2)
    fig, ax = plt.subplots(figsize=(11, fig_height))
    left = np.zeros(len(data))
    for quartile in QUARTILES:
        values = data[f"{quartile}_share_of_matched_pct"].fillna(0).to_numpy()
        bars = ax.barh(labels, values, left=left, color=colors[quartile], label=quartile.upper())
        if show_data_labels:
            ax.bar_label(
                bars,
                labels=[f"{value:.1f}" for value in values],
                label_type="center",
                color="white" if quartile in {"q1", "q2", "q4"} else "#222222",
                fontsize=8,
                fontweight="bold",
            )
        left += values
    ax.set_xlim(0, 100)
    ax.set_xlabel(x_label)
    ax.set_title(title)
    ax.invert_yaxis()
    ax.legend(ncol=4, title="Exposure quartile (Q1 highest)", loc="lower center", bbox_to_anchor=(0.5, -0.24))
    ax.grid(axis="x", alpha=0.2)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / output_name, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_q1_change(
    changes: pd.DataFrame,
    label_col: str,
    title: str,
    output_name: str,
    segment_chart: bool = False,
) -> None:
    data = changes.copy()
    if segment_chart:
        data = data.loc[data["segment_id"].between(1, 10)].sort_values("segment_id")
    labels = data[label_col].astype(str).str.replace(r"^\d+\.\s*", "", regex=True)
    values = data["q1_employment_change"].fillna(0)
    colors = np.where(values.ge(0), "#2b8c6b", "#b23a48")
    fig_height = max(3.2, 0.48 * len(data) + 1.2)
    fig, ax = plt.subplots(figsize=(11, fig_height))
    ax.barh(labels, values, color=colors)
    ax.axvline(0, color="#333333", linewidth=0.8)
    ax.set_xlabel(f"Change in highest-exposure-quartile employment ({BASE_YEAR}–{TARGET_YEAR})")
    ax.set_title(title)
    ax.invert_yaxis()
    ax.grid(axis="x", alpha=0.2)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / output_name, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_segment_quartiles_with_national_benchmark(
    summary: pd.DataFrame,
    year: int,
    output_name: str,
) -> None:
    """Plot segment quartile shares against an equal-quartile national reference."""
    data = summary.loc[
        summary["year"].eq(year) & summary["segment_id"].between(1, 10)
    ].sort_values("segment_id")
    segment_labels = data["segment_name"].astype(str).str.replace(r"^\d+\.\s*", "", regex=True).tolist()
    labels = [*segment_labels, "All Industry Employment (National)"]
    # Leave a visual gap before the national reference row at the bottom.
    positions = np.array([*range(len(segment_labels)), len(segment_labels) + 1], dtype=float)
    colors = {"q1": "#7a0019", "q2": "#d95f02", "q3": "#fdb863", "q4": "#5e81ac"}

    fig, ax = plt.subplots(figsize=(11, 6.8))
    left = np.zeros(len(labels))
    for quartile in QUARTILES:
        segment_values = data[f"{quartile}_share_of_matched_pct"].fillna(0).to_numpy()
        values = np.concatenate((segment_values, [25.0]))
        bars = ax.barh(
            positions,
            values,
            left=left,
            color=colors[quartile],
            label=quartile.upper(),
        )
        # Distinguish the constructed national benchmark without changing its
        # quartile colors. The first bar remains an ordinary segment bar, so
        # Matplotlib's legend uses the solid segment designation.
        bars[-1].set_hatch("///")
        bars[-1].set_edgecolor("#222222")
        bars[-1].set_linewidth(1.0)
        left += values

    ax.axhline(len(segment_labels), color="#777777", linewidth=0.8, linestyle="--")
    ax.set_yticks(positions, labels)
    ax.set_xlim(0, 100)
    ax.set_xlabel("Share of segment employment (%)")
    ax.set_title(f"Employment distribution by AI-exposure quartile and segment, {year}")
    ax.invert_yaxis()
    ax.legend(
        ncol=4,
        title="Exposure quartile (Q1 highest)",
        loc="lower center",
        bbox_to_anchor=(0.5, -0.22),
    )
    ax.grid(axis="x", alpha=0.2)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / output_name, dpi=200, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    exposure = load_exposure()
    crosswalk = load_bls_crosswalk()
    crosswalk_estimates, crosswalk_components = build_complete_crosswalk_estimates(exposure, crosswalk)
    assembler_imputation = pd.DataFrame([build_assembler_imputation(exposure)])

    segment_panel = pd.read_csv(ROOT / "sam_occ_segment_totals_2024_2034.csv", dtype={"occcd": str})
    segment_snapshot = pd.read_excel(ROOT / "sam_occ_segment_totals_2030.xlsx", dtype={"occcd": str})
    stage_snapshot = pd.read_excel(ROOT / "sam_occ_stage_totals_2030.xlsx", dtype={"occcd": str})
    for name, frame in {
        "segment panel": segment_panel,
        "segment snapshot": segment_snapshot,
        "stage snapshot": stage_snapshot,
    }.items():
        methods = set(frame["methodology"].dropna().astype(str))
        if methods != {METHODOLOGY}:
            raise ValueError(f"{name} contains unexpected methodologies: {sorted(methods)}")

    segment_panel = merge_exposure(segment_panel, exposure, crosswalk_estimates)
    segment_snapshot = merge_exposure(segment_snapshot, exposure, crosswalk_estimates)
    stage_snapshot = merge_exposure(stage_snapshot, exposure, crosswalk_estimates)
    stage_long = long_stage_employment(stage_snapshot)

    segment_summary = summarize(segment_panel.loc[segment_panel["year"].isin([BASE_YEAR, TARGET_YEAR])], ["segment_id", "segment_name"])
    stage_summary = summarize(stage_long, ["stage_clean"])
    segment_change = change_table(segment_summary, ["segment_id", "segment_name"])
    stage_change = change_table(stage_summary, ["stage_clean"])
    unmatched = unmatched_diagnostic(segment_panel)

    segment_panel.to_csv(OUTPUT_DIR / "occupation_segment_exposure_2024_2034.csv", index=False)
    segment_snapshot.to_excel(OUTPUT_DIR / "occupation_segment_exposure_2030.xlsx", index=False)
    stage_snapshot.to_excel(OUTPUT_DIR / "occupation_stage_exposure_2030.xlsx", index=False)
    segment_summary.to_csv(OUTPUT_DIR / "segment_exposure_summary_2024_2030.csv", index=False)
    stage_summary.to_csv(OUTPUT_DIR / "stage_exposure_summary_2024_2030.csv", index=False)
    segment_change.to_csv(OUTPUT_DIR / "segment_exposure_change_2024_2030.csv", index=False)
    stage_change.to_csv(OUTPUT_DIR / "stage_exposure_change_2024_2030.csv", index=False)
    unmatched.to_csv(OUTPUT_DIR / "unmatched_soc_diagnostic.csv", index=False)
    assembler_imputation.to_csv(OUTPUT_DIR / "exposure_imputation_audit.csv", index=False)
    crosswalk_estimates.to_csv(OUTPUT_DIR / "bls_crosswalk_application_audit.csv", index=False)
    crosswalk_components.to_csv(OUTPUT_DIR / "bls_crosswalk_component_audit.csv", index=False)

    with pd.ExcelWriter(OUTPUT_DIR / "ai_exposure_analysis_tables.xlsx", engine="openpyxl") as writer:
        segment_summary.to_excel(writer, sheet_name="segment_summary", index=False)
        segment_change.to_excel(writer, sheet_name="segment_change", index=False)
        stage_summary.to_excel(writer, sheet_name="stage_summary", index=False)
        stage_change.to_excel(writer, sheet_name="stage_change", index=False)
        unmatched.to_excel(writer, sheet_name="unmatched_soc", index=False)
        assembler_imputation.to_excel(writer, sheet_name="imputation_audit", index=False)
        crosswalk_estimates.to_excel(writer, sheet_name="crosswalk_audit", index=False)
        crosswalk_components.to_excel(writer, sheet_name="crosswalk_components", index=False)

    plot_quartile_shares(
        segment_summary,
        "segment_id",
        "segment_name",
        BASE_YEAR,
        f"Employment distribution by AI-exposure quartile and segment, {BASE_YEAR}",
        "segment_exposure_quartile_shares_2024.png",
        "Share of segment employment (%)",
        exclude_segment_11=True,
    )
    plot_quartile_shares(
        segment_summary,
        "segment_id",
        "segment_name",
        BASE_YEAR,
        f"Employment distribution by AI-exposure quartile and segment, {BASE_YEAR}",
        "segment_exposure_quartile_shares_2024_labeled.png",
        "Share of segment employment (%)",
        exclude_segment_11=True,
        show_data_labels=True,
    )
    plot_quartile_shares(
        segment_summary,
        "segment_id",
        "segment_name",
        TARGET_YEAR,
        f"Employment distribution by AI-exposure quartile and segment, {TARGET_YEAR}",
        "segment_exposure_quartile_shares_2030.png",
        "Share of segment employment (%)",
        exclude_segment_11=True,
    )
    plot_quartile_shares(
        stage_summary,
        "stage_clean",
        "stage_clean",
        TARGET_YEAR,
        f"Employment distribution by AI-exposure quartile and stage, {TARGET_YEAR}",
        "stage_exposure_quartile_shares_2030.png",
        "Share of stage employment (%)",
    )
    plot_segment_quartiles_with_national_benchmark(
        segment_summary,
        BASE_YEAR,
        "segment_exposure_quartile_shares_2024_national_benchmark.png",
    )
    plot_q1_change(
        segment_change,
        "segment_name",
        "Change in highest AI-exposure-quartile employment by segment",
        "segment_high_exposure_employment_change_2024_2030.png",
        segment_chart=True,
    )
    plot_q1_change(
        stage_change,
        "stage_clean",
        "Change in highest AI-exposure-quartile employment by stage",
        "stage_high_exposure_employment_change_2024_2030.png",
    )

    nonoverlap = segment_panel.loc[segment_panel["segment_id"].between(1, 10)]
    target = nonoverlap.loc[nonoverlap["year"].eq(TARGET_YEAR)]
    total = target["employment_auto"].sum()
    covered = target.loc[target["exposure_match"], "employment_auto"].sum()
    print(f"Wrote analysis outputs to {OUTPUT_DIR}")
    print(f"Exact detailed SOC matches: {target.loc[target['exposure_exact_match'], 'occcd'].nunique()} / {target['occcd'].nunique()}")
    print(f"Complete BLS crosswalk matches: {target.loc[target['exposure_crosswalked'] & ~target['exposure_imputed'], 'occcd'].nunique()}")
    print(f"Residual-imputed BLS crosswalk matches: {target.loc[target['exposure_imputed'], 'occcd'].nunique()}")
    print(f"Usable SOC matches after imputation: {target.loc[target['exposure_match'], 'occcd'].nunique()} / {target['occcd'].nunique()}")
    print(f"{TARGET_YEAR} employment coverage: {covered / total:.2%}")


if __name__ == "__main__":
    main()
