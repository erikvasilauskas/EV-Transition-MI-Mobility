"""Interactive dashboard for Michigan occupational forecasts.

Run locally with:
    streamlit run dashboards/occupation_forecast_dashboard.py
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = REPO_ROOT / "data" / "processed" / "mi_occ_segment_totals_2024_2034.csv"
CORE_SERIES_PATH = REPO_ROOT / "data" / "processed" / "mi_qcew_segment_employment_timeseries_coreauto_extended_compare.csv"
COLORS_PATH = REPO_ROOT / "config" / "colors.json"
DEFAULT_METHOD = "lightcast_moody"

with open(COLORS_PATH, "r", encoding="utf-8") as _f:
    COLORS = json.load(_f)
TEAL = COLORS.get("teal", "#2B9CB4")


@st.cache_data(show_spinner=False)
def load_forecasts() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH)
    df["methodology"] = df["methodology"].astype(str)
    df["segment_name"] = df["segment_name"].astype(str)
    df["soctitle"] = df["soctitle"].astype(str)
    df["ep_edu_grouped"] = df["ep_edu_grouped"].fillna("Unreported")
    return df


@st.cache_data(show_spinner=False)
def load_core_series() -> pd.DataFrame:
    df = pd.read_csv(CORE_SERIES_PATH)
    df["segment_name"] = df["segment_name"].astype(str)
    df["source"] = df["forecast_source"].fillna("Observed QCEW")
    df["source"] = df["source"].replace({"BLS": "BLS growth", "Moody": "Moody growth"})
    return df


def format_number(value: float, suffix: str = "") -> str:
    if pd.isna(value):
        return "-"
    if abs(value) >= 1_000_000:
        return f"{value/1_000_000:.1f}M{suffix}"
    if abs(value) >= 1_000:
        return f"{value/1_000:.1f}K{suffix}"
    return f"{value:,.0f}{suffix}"


def render_method_card(
    container, method_name: str, latest: float, base: float, delta: float, delta_pct: float, base_year: int, latest_year: int
) -> None:
    pct_text = f" ({delta_pct:.1f}%)" if not np.isnan(delta_pct) else ""
    container.markdown(
        f"""
        <div style=\"background-color:#F5F9FA;padding:16px;border-radius:10px;border-left:4px solid {TEAL};\">
            <div style=\"font-size:0.85rem;color:#4A5568;margin-bottom:4px;\">{method_name}</div>
            <div style=\"font-size:2rem;font-weight:600;color:#1A202C;\">{format_number(latest)}<span style=\"font-size:1rem;font-weight:400;color:#718096;\"> ({latest_year})</span></div>
            <div style=\"font-size:0.95rem;font-weight:500;color:{TEAL};margin-top:6px;\">Δ {format_number(delta)}{pct_text}</div>
            <div style=\"font-size:0.8rem;color:#718096;margin-top:4px;\">Baseline {base_year}: {format_number(base)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def summarize_employment(df: pd.DataFrame, year: int) -> pd.DataFrame:
    summary = (
        df[df["year"] == year]
        .groupby("methodology", as_index=False)["employment"]
        .sum()
        .sort_values("employment", ascending=False)
    )
    summary["employment_fmt"] = summary["employment"].apply(format_number)
    return summary


def aggregate_by_segment(df: pd.DataFrame, year: int) -> pd.DataFrame:
    return (
        df[df["year"] == year]
        .groupby(["segment_id", "segment_name", "methodology"], as_index=False)["employment"]
        .sum()
    )


def aggregate_by_education(df: pd.DataFrame, year: int | None = None) -> pd.DataFrame:
    filtered = df if year is None else df[df["year"] == year]
    return (
        filtered.groupby(["ep_edu_grouped", "methodology", "year"], as_index=False)["employment"]
        .sum()
        .sort_values(["ep_edu_grouped", "year", "methodology"])
    )


def build_methodology_selector(all_methods: List[str]) -> List[str]:
    default = DEFAULT_METHOD if DEFAULT_METHOD in all_methods else all_methods
    methods = st.sidebar.multiselect(
        "Methodology assumptions",
        options=all_methods,
        default=default,
        help="Toggle to compare attribution (BEA vs. Lightcast) and growth (Moody vs. BLS).",
    )
    if not methods:
        st.warning("Select at least one methodology to view results. Defaulting to all options.")
        return all_methods
    return methods


def build_year_selector(years: List[int], label: str, default: int | None = None) -> int:
    return st.slider(
        label,
        min_value=min(years),
        max_value=max(years),
        value=default or max(years),
        step=1,
    )


def layout_overview(df: pd.DataFrame, selected_methods: List[str]) -> None:
    st.subheader("Key Highlights")
    latest_year = df["year"].max()
    base_year = df["year"].min()

    method_metrics = []
    for method in selected_methods:
        method_df = df[df["methodology"] == method]
        base_total = method_df[method_df["year"] == base_year]["employment"].sum()
        latest_total = method_df[method_df["year"] == latest_year]["employment"].sum()
        delta_abs = latest_total - base_total
        delta_pct = (delta_abs / base_total * 100) if base_total else np.nan
        method_metrics.append(
            {
                "method": method,
                "base": base_total,
                "latest": latest_total,
                "delta": delta_abs,
                "pct": delta_pct,
            }
        )

    if not method_metrics:
        st.info("Select at least one methodology to view results.")
        return

    cards_per_row = 3 if len(method_metrics) > 2 else len(method_metrics)
    for idx, metric in enumerate(method_metrics):
        if idx % cards_per_row == 0:
            cols = st.columns(cards_per_row)
        render_method_card(
            cols[idx % cards_per_row],
            metric["method"],
            metric["latest"],
            metric["base"],
            metric["delta"],
            metric["pct"],
            base_year,
            latest_year,
        )

    summary_df = pd.DataFrame(method_metrics)
    summary_df = summary_df.assign(
        **{
            f"Employment {base_year}": summary_df["base"],
            f"Employment {latest_year}": summary_df["latest"],
            "Abs change": summary_df["delta"],
            "% change": summary_df["pct"],
        }
    )[
        ["method", f"Employment {base_year}", f"Employment {latest_year}", "Abs change", "% change"]
    ]
    summary_df = summary_df.rename(columns={"method": "Methodology"})
    summary_df["Abs change"] = summary_df["Abs change"].apply(format_number)
    summary_df[f"Employment {base_year}"] = summary_df[f"Employment {base_year}"].apply(format_number)
    summary_df[f"Employment {latest_year}"] = summary_df[f"Employment {latest_year}"].apply(format_number)
    summary_df["% change"] = summary_df["% change"].apply(
        lambda v: f"{v:.1f}%" if not np.isnan(v) else "-"
    )

    with st.expander("Methodology comparison", expanded=False):
        st.dataframe(summary_df.set_index("Methodology"), use_container_width=True)

    st.caption("Source: data/processed/mi_occ_segment_totals_2024_2034.csv")


def layout_segments(df: pd.DataFrame, selected_methods: List[str], years: List[int]) -> None:
    st.subheader("Segment-Level View")
    seg_year = build_year_selector(years, "Select year for segment snapshot", default=max(years))
    seg_data = aggregate_by_segment(df[df["methodology"].isin(selected_methods)], seg_year)
    seg_data = seg_data[seg_data["segment_id"] != 0]

    if seg_data.empty:
        st.info("No segment-level data available for the selected settings.")
        return

    fig = px.bar(
        seg_data,
        x="employment",
        y="segment_name",
        color="methodology",
        orientation="h",
        title=f"Segment employment in {seg_year}",
        labels={"employment": "Employment", "segment_name": "Segment", "methodology": "Method"},
        barmode="group",
        height=600,
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Detailed segment table")
    st.dataframe(
        seg_data.sort_values(["segment_id", "methodology"])
        .set_index(["segment_id", "segment_name", "methodology"]),
        use_container_width=True,
    )

    st.caption(
        "Segments reflect Michigan automotive supply chain categories (segments 1-10). "
        "Baseline (2024) values carry the MCDA staffing pattern, adjusted per selected methodology."
    )


def layout_time_series(df: pd.DataFrame, selected_methods: List[str], core_df: pd.DataFrame) -> None:
    st.subheader("Stage / Time Horizon View")
    stage_choice = st.selectbox(
        "Aggregate by",
        ["All segments", "Individual segment"],
        help="Choose to view statewide totals or isolate a single supply segment over time.",
    )

    stage_df = df[df["methodology"].isin(selected_methods)].copy()
    stage_df = stage_df[stage_df["segment_id"] != 0]

    seg_id: int | None = None
    if stage_choice == "Individual segment":
        segment_options = (
            stage_df[["segment_id", "segment_name"]]
            .drop_duplicates()
            .sort_values(["segment_id"])
            .assign(label=lambda d: d["segment_id"].astype(str) + " - " + d["segment_name"])
        )
        if segment_options.empty:
            st.info("No segment-level data available for the selected settings.")
            return
        selected_segment = st.selectbox("Select segment", options=segment_options["label"])
        seg_id = int(selected_segment.split(" - ")[0])
        stage_df = stage_df[stage_df["segment_id"] == seg_id]

    if stage_df.empty:
        st.info("No data available for the selected settings.")
        return

    timeline = (
        stage_df.groupby(["year", "methodology"], as_index=False)["employment"].sum()
        .sort_values(["methodology", "year"])
    )

    fig = px.line(
        timeline,
        x="year",
        y="employment",
        color="methodology",
        markers=True,
        title="Employment trajectory",
        labels={"employment": "Employment", "year": "Year", "methodology": "Method"},
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Extended core automotive context (2001-2034)")
    core_subset = core_df.copy()
    if seg_id is not None:
        core_subset = core_subset[core_subset["segment_id"] == seg_id]

    if core_subset.empty:
        st.info("No extended series available for the selected segment.")
    else:
        core_timeline = (
            core_subset.groupby(["year", "source"], as_index=False)["employment_qcew"]
            .sum()
            .sort_values(["source", "year"])
        )
        fig_core = px.line(
            core_timeline,
            x="year",
            y="employment_qcew",
            color="source",
            markers=True,
            labels={"employment_qcew": "Employment", "source": "Growth path", "year": "Year"},
            title="Historical baseline and growth comparisons",
        )
        st.plotly_chart(fig_core, use_container_width=True)
        st.caption(
            "Extended series blends historical QCEW employment (2001 onward) with core automotive projections using BLS- and Moody-based growth paths."
        )


def layout_occupation_insights(df: pd.DataFrame, selected_methods: List[str]) -> None:
    st.subheader("Occupation Explorer")

    occ_options = (
        df[["occcd", "soctitle"]]
        .drop_duplicates()
        .assign(label=lambda d: d["occcd"] + " - " + d["soctitle"])
        .sort_values("label")
    )

    selected_occ = st.selectbox(
        "Choose an occupation",
        options=occ_options["label"],
        index=min(5, len(occ_options) - 1),
        help="Select SOC occupation to inspect employment change under each methodology.",
    )
    occ_code = selected_occ.split(" - ")[0]

    occ_df = df[(df["occcd"] == occ_code) & (df["methodology"].isin(selected_methods))]

    trend = occ_df.groupby(["year", "methodology"], as_index=False)["employment"].sum()
    fig = px.line(
        trend,
        x="year",
        y="employment",
        color="methodology",
        title=f"{selected_occ}: Employment forecast",
        markers=True,
        labels={"employment": "Employment", "year": "Year", "methodology": "Method"},
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Methodology snapshot")
    compare_years = [df["year"].min(), 2030]
    snapshot = (
        occ_df[occ_df["year"].isin(compare_years)]
        .pivot_table(index="methodology", columns="year", values="employment")
        .assign(abs_change=lambda d: d[compare_years[1]] - d[compare_years[0]])
        .assign(pct_change=lambda d: np.where(d[compare_years[0]] > 0, d["abs_change"] / d[compare_years[0]] * 100, np.nan))
        .rename(columns={compare_years[0]: f"Employment {compare_years[0]}", compare_years[1]: "Employment 2030"})
        .sort_values("abs_change", ascending=False)
    )
    st.dataframe(snapshot, use_container_width=True)

    st.markdown("### Occupation table")
    table_method_default = DEFAULT_METHOD if DEFAULT_METHOD in selected_methods else selected_methods[0]
    table_method = st.selectbox(
        "Table methodology",
        options=selected_methods,
        index=selected_methods.index(table_method_default) if table_method_default in selected_methods else 0,
        help="Choose which methodology to use for the sortable occupation table.",
    )

    table_df = df[df["methodology"] == table_method].copy()

    segment_options = (
        table_df[table_df["segment_id"] != 0][["segment_id", "segment_name"]]
        .drop_duplicates()
        .sort_values("segment_id")
        .assign(label=lambda d: d["segment_id"].astype(str) + " - " + d["segment_name"])
    )
    segment_labels = segment_options["label"].tolist()
    selected_segment_labels = st.multiselect(
        "Filter segments",
        options=segment_labels,
        default=segment_labels,
        help="Limit the table to specific supply segments (defaults to all).",
    )
    if selected_segment_labels:
        segment_ids = {int(label.split(" - ")[0]) for label in selected_segment_labels}
        table_df = table_df[table_df["segment_id"].isin(segment_ids)]
    else:
        table_df = table_df[table_df["segment_id"] != 0]

    edu_options = sorted(table_df["ep_edu_grouped"].unique())
    selected_edus = st.multiselect(
        "Education groups",
        options=edu_options,
        default=edu_options,
        help="Filter occupations by education requirements.",
    )
    if selected_edus:
        table_df = table_df[table_df["ep_edu_grouped"].isin(selected_edus)]

    if table_df.empty:
        st.info("No occupation data remains after applying the filters.")
        return

    available_years = sorted(table_df["year"].unique())
    base_year = available_years[0]
    target_year = 2030 if 2030 in available_years else available_years[-1]

    metrics = (
        table_df[table_df["year"].isin([base_year, target_year])]
        .groupby(["occcd", "soctitle", "year"], as_index=False)["employment"]
        .sum()
    )
    pivot = (
        metrics.pivot(index=["occcd", "soctitle"], columns="year", values="employment")
        .fillna(0)
    )
    pivot["abs_change"] = pivot.get(target_year, 0) - pivot.get(base_year, 0)
    pivot["pct_change"] = np.where(
        pivot.get(base_year, 0) > 0,
        pivot["abs_change"] / pivot.get(base_year, 0) * 100,
        np.nan,
    )

    pivot = pivot.reset_index().rename(
        columns={
            base_year: f"Employment {base_year}",
            target_year: f"Employment {target_year}",
        }
    )

    sort_options = [
        f"Employment {base_year}",
        f"Employment {target_year}",
        "abs_change",
        "pct_change",
    ]
    sort_choice = st.selectbox("Sort table by", options=sort_options, index=2)
    ascending = st.checkbox("Sort ascending", value=False)

    pivot = pivot.sort_values(sort_choice, ascending=ascending)
    st.dataframe(pivot, use_container_width=True)

    st.caption(
        "Use the filters above to focus by methodology, segment, or education pathway. "
        "Values aggregate employment across the selected methodology for the chosen grouping."
    )


def layout_data_access(df: pd.DataFrame, core_df: pd.DataFrame) -> None:
    st.subheader("Data Access & Notes")
    st.markdown(
        textwrap.dedent(
            """
            - **Occupation detail**: `data/processed/mi_occ_segment_totals_2024_2034.csv`
            - **Core automotive time series**: `data/processed/mi_qcew_segment_employment_timeseries_coreauto_extended_compare.csv`
            - **Pipeline**: `scripts/occupation_forecasts_from_segment_totals.py`
            - **Segments**: Michigan automotive supply chain (1-10) plus statewide total (segment 0 in occupation file)
            """
        )
    )

    st.markdown("#### Preview (occupation forecasts)")
    st.dataframe(df.head(), use_container_width=True)

    st.markdown("#### Preview (core automotive series)")
    st.dataframe(core_df.head(), use_container_width=True)

    st.download_button(
        "Download occupation data (CSV)",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name="mi_occ_segment_totals_filtered.csv",
        mime="text/csv",
    )

    st.download_button(
        "Download core automotive series (CSV)",
        data=core_df.to_csv(index=False).encode("utf-8"),
        file_name="mi_qcew_segment_employment_timeseries_coreauto_extended_compare.csv",
        mime="text/csv",
    )


# --- Streamlit App ---
st.set_page_config(page_title="MI Occupational Forecast Dashboard", layout="wide")

st.title("Michigan Automotive Occupational Forecasts")
st.caption(
    "Interactive exploration of occupational employment forecasts (2024-2034) and extended historical context across methodologies, segments, and education groupings."
)

forecasts = load_forecasts()
core_series = load_core_series()
all_years = sorted(forecasts["year"].unique())
all_methods = sorted(forecasts["methodology"].unique())
selected_methods = build_methodology_selector(all_methods)
filtered_df = forecasts[forecasts["methodology"].isin(selected_methods)]

overview_tab, segment_tab, stage_tab, occupation_tab, data_tab = st.tabs(
    [
        "Overview",
        "Segments",
        "Stage / Horizon",
        "Occupation Explorer",
        "Data & Notes",
    ]
)

with overview_tab:
    layout_overview(filtered_df, selected_methods)

with segment_tab:
    layout_segments(filtered_df, selected_methods, all_years)

with stage_tab:
    layout_time_series(filtered_df, selected_methods, core_series)

with occupation_tab:
    layout_occupation_insights(filtered_df, selected_methods)

with data_tab:
    layout_data_access(filtered_df, core_series)
