"""Visualize employment projection rates across NAICS industries."""

from __future__ import annotations

from pathlib import Path

import altair as alt
import pandas as pd


def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"naics_code": str})
    df["stage"] = df["stage"].fillna("Unknown")
    df["stage_prefix"] = df["stage"].str.lower().map({"upstream": "U", "downstream": "D"}).fillna("O")
    df["naics_label"] = (
        df["stage_prefix"]
        + " | "
        + df["naics_code"].str.zfill(4)
        + " – "
        + df["naics_title"]
    )
    return df


def melt_rates(df: pd.DataFrame) -> pd.DataFrame:
    rate_cols = [
        "moodys_mi_pct_change_2024_2030_employment",
        "moodys_us_pct_change_2024_2030_employment",
        "mi_dtmb_six_year_rate",
        "bls_us_six_year_employment_rate_change",
    ]

    rate_mapping = {
        "moodys_mi_pct_change_2024_2030_employment": "Moody's MI",
        "moodys_us_pct_change_2024_2030_employment": "Moody's US",
        "mi_dtmb_six_year_rate": "DTMB MI",
        "bls_us_six_year_employment_rate_change": "BLS US",
    }

    melted = df.melt(
        id_vars=[
            "orig_sort",
            "naics_code",
            "naics_title",
            "segment_id",
            "segment_name",
            "stage",
            "stage_prefix",
            "naics_label",
            "employment_qcew_2024",
        ],
        value_vars=rate_cols,
        var_name="source",
        value_name="rate",
    )
    melted.dropna(subset=["rate"], inplace=True)
    melted["source"] = melted["source"].map(rate_mapping)
    melted["projected_employment"] = (
        melted["employment_qcew_2024"] * (1 + melted["rate"])
    ).round()
    return melted


def build_chart(df_long: pd.DataFrame) -> alt.Chart:
    sort_field = alt.SortField("orig_sort", order="ascending")
    x_enc = alt.X(
        "naics_label:N",
        sort=sort_field,
        title="Stage | Code – Title",
        axis=alt.Axis(labelAngle=-40),
    )
    y_enc = alt.Y("rate:Q", axis=alt.Axis(format="%"), title="Six-year Employment Change Rate")
    color_enc = alt.Color("source:N", title="Projection Source")
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
                alt.Tooltip("rate", format=".2%"),
                alt.Tooltip("employment_qcew_2024", title="QCEW Employment 2024", format=","),
                alt.Tooltip("projected_employment", title="Projected Employment (2030 est.)", format=","),
                "segment_name",
                "stage",
            ],
        )
        .properties(width=1200, height=600)
        .interactive()
    )
    return chart


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    data_path = repo_root / "data" / "intermediate" / "employment_projection_comparison.csv"
    output_path = repo_root / "reports" / "employment_projection_comparison_chart.html"

    df = load_data(data_path)
    df_long = melt_rates(df)
    chart = build_chart(df_long)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    chart.save(output_path)
    print(f"Wrote employment projection chart to {output_path}")


if __name__ == "__main__":
    main()
