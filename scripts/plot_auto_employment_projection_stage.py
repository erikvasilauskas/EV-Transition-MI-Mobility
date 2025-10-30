"""Plot stage-level employment projections for all share/rate scenarios."""

from __future__ import annotations

from pathlib import Path

import altair as alt
import pandas as pd


def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["stage"] = df["stage"].astype(str)
    return df


def build_chart(df: pd.DataFrame) -> alt.Chart:
    df["scenario"] = df["share_label"] + " × " + df["projection_label"]

    chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X(
                "stage:N",
                sort=["Upstream", "Core", "Downstream", "Unknown", "Upstream+Core"],
                title="Stage",
            ),
            y=alt.Y("projected_employment:Q", title="Projected Employment"),
            color=alt.Color("scenario:N", title="Scenario"),
            tooltip=[
                "stage",
                "share_label",
                "projection_label",
                alt.Tooltip("base_employment", format=","),
                alt.Tooltip("projected_employment", format=","),
            ],
        )
        .properties(width=800, height=400)
        .interactive()
    )
    return chart


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    data_path = repo_root / "data" / "processed" / "auto_employment_projections" / "auto_employment_projection_stage_summary.csv"
    output_path = repo_root / "reports" / "auto_employment_projection_stage_chart.html"

    df = load_data(data_path)
    chart = build_chart(df)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    chart.save(output_path)
    print(f"Wrote stage projection chart to {output_path}")


if __name__ == "__main__":
    main()
