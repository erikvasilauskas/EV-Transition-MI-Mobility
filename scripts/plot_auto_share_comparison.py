"""Visualize automotive attribution shares across NAICS industries.

Reads the consolidated comparison table produced by
``build_auto_share_comparison.py`` and creates a long-form dataset,
then plots the different share estimates per NAICS using Altair. The
chart is saved to ``reports/auto_share_comparison_chart.html``.
"""

from __future__ import annotations

from pathlib import Path

import altair as alt
import pandas as pd


def load_comparison(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"naics_code": str})
    df["naics_code"] = df["naics_code"].str.strip()
    return df


def melt_shares(df: pd.DataFrame) -> pd.DataFrame:
    share_cols = [
        "sam_auto_share",
        "sam_auto_share_us",
        "lightcast_share",
        "lightcast_share_us",
        "bea_summary_total_output_share",
        "bea_detail_intermediate_share",
        "bea_detail_total_output_share",
        "mrio_indirect_share",
        "mrio_total_share",
    ]

    melted = df.melt(
        id_vars=[
            "naics_code",
            "naics_title",
            "segment_id",
            "segment_name",
            "stage",
            "employment_qcew_2024",
        ],
        value_vars=share_cols,
        var_name="source",
        value_name="auto_share",
    )
    melted.dropna(subset=["auto_share"], inplace=True)
    melted["auto_employment"] = (melted["auto_share"] * melted["employment_qcew_2024"]).round()
    return melted


def make_chart(df_long: pd.DataFrame) -> alt.Chart:
    df_long["stage"] = df_long["stage"].fillna("Unknown")
    special_codes = {"5413", "5414", "5417"}
    upstream_mask = df_long["stage"].str.lower() == "upstream"
    df_long = df_long[upstream_mask | df_long["naics_code"].isin(special_codes)].copy()

    stage_map = {"upstream": "U", "downstream": "D"}
    df_long["stage_prefix"] = df_long["stage"].str.lower().map(stage_map).fillna("O")
    df_long["naics_label"] = (
        df_long["stage_prefix"]
        + " | "
        + df_long["naics_code"].str.zfill(4)
        + " – "
        + df_long["naics_title"]
    )

    sort_field = alt.SortField("naics_code", order="ascending")
    x_enc = alt.X(
        "naics_label:N",
        title="Stage | Code – Title",
        sort=sort_field,
        axis=alt.Axis(labelAngle=-40),
    )
    y_enc = alt.Y("auto_share:Q", axis=alt.Axis(format="%"), title="Automotive Share")
    color_enc = alt.Color("source:N", title="Share Source")
    shape_enc = alt.Shape("stage_prefix:N", title="Stage Prefix", sort=["U", "D", "O"])

    chart = (
        alt.Chart(df_long)
        .mark_circle(size=80)
        .encode(
            x=x_enc,
            y=y_enc,
            color=color_enc,
            shape=shape_enc,
            tooltip=[
                "naics_code",
                "naics_title",
                "source",
                alt.Tooltip("auto_share", format=".2%"),
                alt.Tooltip("employment_qcew_2024", title="QCEW Employment 2024", format=","),
                alt.Tooltip("auto_employment", title="Attributed Employment", format=","),
                "segment_name",
                "stage",
            ],
        )
    )

    return chart.properties(width=1200, height=600).interactive()


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    comparison_path = repo_root / "data" / "intermediate" / "auto_share_comparison.csv"
    output_path = repo_root / "reports" / "auto_share_comparison_chart.html"

    df = load_comparison(comparison_path)
    df_long = melt_shares(df)
    chart = make_chart(df_long)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    chart.save(output_path)
    print(f"Wrote chart to {output_path}")


if __name__ == "__main__":
    main()
