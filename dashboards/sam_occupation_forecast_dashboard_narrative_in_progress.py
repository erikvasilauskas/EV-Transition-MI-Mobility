"""Streamlit dashboard for SAM-standard automotive employment projections.

Run locally with:
    streamlit run dashboards/sam_occupation_forecast_dashboard.py
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

REPO_ROOT = Path(__file__).resolve().parents[1]
SAM_DIR = REPO_ROOT / "data" / "processed" / "sam_auto_dashboard"

OCC_PATH = SAM_DIR / "sam_occ_segment_totals_2024_2034.csv"
SEGMENT_TS_PATH = SAM_DIR / "sam_employment_segment_timeseries.csv"
STAGE_TS_PATH = SAM_DIR / "sam_employment_stage_timeseries.csv"
NAICS_TS_PATH = SAM_DIR / "sam_employment_naics_timeseries.csv"
SEGMENT_LOOKUP_PATH = REPO_ROOT / "data" / "lookups" / "segment_assignments.csv"
COLORS_PATH = REPO_ROOT / "config" / "colors.json"

DEFAULT_METHOD = "sam_mi_moodys_mi"
PROJECTION_LABELS = {
    "moodys_mi": "Moody's MI",
    "moodys_us": "Moody's US",
    "dtmb_mi": "DTMB MI",
    "bls_us": "BLS US",
}

with open(COLORS_PATH, "r", encoding="utf-8") as f:
    COLORS = json.load(f)
TEAL = COLORS.get("teal", "#2B9CB4")


def projection_slug(methodology: str) -> str:
    parts = methodology.split("_")
    if len(parts) >= 3:
        return "_".join(parts[2:])
    return methodology


def projection_display(slug: str) -> str:
    return PROJECTION_LABELS.get(slug, slug.replace("_", " ").title())


def methodology_display(methodology: str) -> str:
    return f"SAM MI • {projection_display(projection_slug(methodology))}"


@st.cache_data(show_spinner=False)
def load_forecasts() -> pd.DataFrame:
    df = pd.read_csv(OCC_PATH)
    df["methodology"] = df["methodology"].astype(str)
    df["segment_name"] = df["segment_name"].astype(str)
    df["soctitle"] = df["soctitle"].astype(str)
    df["ep_edu_grouped"] = df["ep_edu_grouped"].fillna("Unreported")
    df["method_label"] = df["methodology"].map(methodology_display)
    return df


@st.cache_data(show_spinner=False)
def load_stage_series() -> pd.DataFrame:
    df = pd.read_csv(STAGE_TS_PATH)
    df["stage"] = df["stage"].astype(str)
    df["value_type"] = df["value_type"].astype(str)
    df["forecast_source"] = df["forecast_source"].astype(str)
    df["projection_label"] = df["projection_label"].astype(str)
    df["projection_method"] = df["forecast_source"].astype(str)
    df["methodology"] = df["projection_method"].apply(lambda s: f"sam_mi_{s}")
    df["method_label"] = df["methodology"].map(methodology_display)
    return df


@st.cache_data(show_spinner=False)
def load_segment_timeseries() -> pd.DataFrame:
    df = pd.read_csv(SEGMENT_TS_PATH)
    df["segment_name"] = df["segment_name"].astype(str)
    df["adjustment_source"] = df["adjustment_source"].astype(str)
    df["forecast_source"] = df["forecast_source"].astype(str)
    df["methodology"] = df["forecast_source"].apply(lambda s: f"sam_mi_{s}")
    df["method_label"] = df["methodology"].map(methodology_display)
    return df


@st.cache_data(show_spinner=False)
def load_naics_baseline() -> pd.DataFrame:
    df = pd.read_csv(NAICS_TS_PATH)
    df = df[(df["year"] == 2024) & (df["value_type"].str.upper() == "QCEW")]
    df = df[["segment_id", "segment_name", "stage", "naics_code", "naics_title", "employment_raw", "employment_auto", "share_applied"]].copy()
    df["segment_name"] = df["segment_name"].astype(str)
    df["stage"] = df["stage"].astype(str)
    df["naics_code"] = df["naics_code"].astype(str)
    df["naics_title"] = df["naics_title"].astype(str)
    return df


@st.cache_data(show_spinner=False)
def load_segment_lookup() -> pd.DataFrame:
    df = pd.read_csv(SEGMENT_LOOKUP_PATH)
    df["segment_id"] = pd.to_numeric(df["segment_id"], errors="coerce").fillna(0).astype(int)
    df["segment_name"] = df["segment_name"].astype(str)
    df["stage"] = df["stage"].astype(str)
    df["naics_code"] = df["naics_code"].astype(str)
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
    container, method_label: str, latest: float, base: float, delta: float, delta_pct: float, base_year: int, latest_year: int
) -> None:
    pct_text = f" ({delta_pct:.1f}%)" if not np.isnan(delta_pct) else ""
    container.markdown(
        f"""
        <div style="background-color:#F5F9FA;padding:20px;border-radius:12px;border-left:5px solid {TEAL};">
            <div style="font-size:1rem;color:#2D3748;margin-bottom:8px;text-transform:uppercase;letter-spacing:0.05em;">{method_label}</div>
            <div style="font-size:2.6rem;font-weight:600;color:#1A202C;line-height:1.1;">{format_number(latest)}<span style="font-size:1.2rem;font-weight:400;color:#718096;"> ({latest_year})</span></div>
            <div style="font-size:1.2rem;font-weight:600;color:{TEAL};margin-top:10px;">ï¿½ {format_number(delta)}{pct_text}</div>
            <div style="font-size:0.95rem;color:#4A5568;margin-top:6px;">Baseline {base_year}: {format_number(base)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def summarize_employment(df: pd.DataFrame, year: int) -> pd.DataFrame:
    summary = (
        df[df["year"] == year]
        .groupby(["methodology", "method_label"], as_index=False)["employment"]
        .sum()
        .sort_values("employment", ascending=False)
    )
    summary["employment_fmt"] = summary["employment"].apply(format_number)
    return summary


def aggregate_by_segment(df: pd.DataFrame, year: int) -> pd.DataFrame:
    return (
        df[df["year"] == year]
        .groupby(["segment_id", "segment_name", "methodology", "method_label"], as_index=False)["employment"]
        .sum()
    )


def aggregate_by_education(df: pd.DataFrame, year: int | None = None) -> pd.DataFrame:
    filtered = df if year is None else df[df["year"] == year]
    return (
        filtered.groupby(["ep_edu_grouped", "methodology", "method_label", "year"], as_index=False)["employment"]
        .sum()
        .sort_values(["ep_edu_grouped", "year", "methodology"])
    )


def build_methodology_selector(
    all_methods: List[str], label_map: Dict[str, str]
) -> List[str]:
    options = [label_map[m] for m in all_methods]
    if DEFAULT_METHOD in label_map:
        default_selection = [label_map[DEFAULT_METHOD]]
    else:
        default_selection = options
    chosen_labels = st.sidebar.multiselect(
        "Methodology assumptions",
        options=options,
        default=default_selection,
        help="Toggle projection scenarios to compare SAM-standard employment outcomes.",
    )
    if not chosen_labels:
        st.warning("Select at least one methodology to view results. Defaulting to all options.")
        return all_methods
    label_to_method = {label_map[m]: m for m in all_methods}
    return [label_to_method[label] for label in chosen_labels if label in label_to_method]


def layout_overview(df: pd.DataFrame, selected_methods: List[str]) -> None:
    st.subheader("Overview")
    base_year, latest_year = df["year"].min(), df["year"].max()

    cards = df[df["methodology"].isin(selected_methods)]
    pivot = (
        cards.pivot_table(
            index=["methodology", "method_label"],
            columns="year",
            values="employment",
            aggfunc="sum",
        )
        .reindex(columns=[base_year, latest_year])
        .fillna(0.0)
        .reset_index()
    )
    pivot["abs_change"] = pivot[latest_year] - pivot[base_year]
    pivot["pct_change"] = np.where(
        pivot[base_year] > 0, (pivot["abs_change"] / pivot[base_year]) * 100, np.nan
    )

    cols = st.columns(min(3, len(pivot)))
    for col, (_, row) in zip(cols, pivot.iterrows()):
        render_method_card(
            col,
            row["method_label"],
            row[latest_year],
            row[base_year],
            row["abs_change"],
            row["pct_change"],
            base_year,
            latest_year,
        )

    st.markdown("### Employment totals by methodology")
    summary = (
        pivot[["method_label", base_year, latest_year, "abs_change", "pct_change"]]
        .rename(
            columns={
                base_year: f"Employment {base_year}",
                latest_year: f"Employment {latest_year}",
                "abs_change": "Change",
                "pct_change": "% Change",
            }
        )
        .sort_values(f"Employment {latest_year}", ascending=False)
    )
    summary["Change"] = summary["Change"].apply(format_number)
    summary[f"Employment {base_year}"] = summary[f"Employment {base_year}"].apply(format_number)
    summary[f"Employment {latest_year}"] = summary[f"Employment {latest_year}"].apply(format_number)
    summary["% Change"] = summary["% Change"].apply(lambda v: f"{v:.1f}%" if not np.isnan(v) else "-")
    st.dataframe(summary.set_index("method_label"), use_container_width=True)


def layout_segments(df: pd.DataFrame, selected_methods: List[str], all_years: List[int]) -> None:
    st.subheader("Segment Comparison")
    year_choice = st.slider(
        "Select year",
        min_value=min(all_years),
        max_value=max(all_years),
        value=max(all_years),
        step=1,
    )

    seg_data = aggregate_by_segment(df[df["methodology"].isin(selected_methods)], year_choice)
    seg_data = seg_data[seg_data["segment_id"] != 0]
    if seg_data.empty:
        st.info("No segment data available for the selected settings.")
        return

    fig = px.bar(
        seg_data,
        x="segment_name",
        y="employment",
        color="method_label",
        barmode="group",
        title=f"Segment employment ({year_choice})",
        labels={"employment": "Employment", "segment_name": "Segment", "method_label": "Methodology"},
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Education mix")
    edu_year = st.selectbox(
        "Education distribution year",
        options=sorted(df["year"].unique()),
        index=sorted(df["year"].unique()).index(year_choice) if year_choice in df["year"].unique() else 0,
        help="Compare how employment is distributed across education groups for each methodology.",
    )
    edu_data = aggregate_by_education(df[df["methodology"].isin(selected_methods)], edu_year)
    pivot = (
        edu_data.pivot_table(index="ep_edu_grouped", columns="method_label", values="employment", aggfunc="sum")
        .fillna(0.0)
    )
    pivot = pivot.loc[pivot.sum(axis=1).sort_values(ascending=False).index]
    pivot = pivot.applymap(format_number)
    st.dataframe(pivot, use_container_width=True)


def layout_stage_trends(stage_df: pd.DataFrame, selected_methods: List[str]) -> None:
    st.subheader("Stage / Time Horizon View")
    slugs = {projection_slug(m) for m in selected_methods}
    filtered = stage_df[stage_df["projection_method"].isin(slugs)].copy()
    if filtered.empty:
        st.info("No stage time-series data available for the selected methodologies.")
        return

    metric_choice = st.radio(
        "Employment measure",
        ["Auto-attributed", "Raw (total)"],
        index=0,
        horizontal=True,
    )
    value_col = "employment_auto" if metric_choice == "Auto-attributed" else "employment_raw"

    stage_focus = st.selectbox(
        "Stage focus",
        ["All stages", "Single stage"],
    )
    if stage_focus == "Single stage":
        stage_options = sorted(filtered["stage"].unique())
        stage_choice = st.selectbox("Select stage", options=stage_options)
        plot_df = filtered[filtered["stage"] == stage_choice]
        title = f"{stage_choice} employment timeline"
    else:
        plot_df = filtered.copy()
        plot_df = plot_df.groupby(["year", "method_label"], as_index=False)[value_col].sum()
        title = "Total employment timeline"

    if plot_df.empty:
        st.info("No data to display for the selected filters.")
        return

    if "method_label" not in plot_df.columns:
        plot_df["method_label"] = plot_df["methodology"].map(methodology_display)

    timeline = (
        plot_df.groupby(["year", "method_label"], as_index=False)[value_col]
        .sum()
        .sort_values(["method_label", "year"])
    )
    fig = px.line(
        timeline,
        x="year",
        y=value_col,
        color="method_label",
        markers=True,
        title=title,
        labels={value_col: "Employment", "year": "Year", "method_label": "Methodology"},
    )
    st.plotly_chart(fig, use_container_width=True)


def layout_occupation_insights(
    df: pd.DataFrame,
    selected_methods: List[str],
    label_map: Dict[str, str],
) -> None:
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
    if occ_df.empty:
        st.info("No data for the selected occupation and methodologies.")
        return

    trend = occ_df.groupby(["year", "method_label"], as_index=False)["employment"].sum()
    fig = px.line(
        trend,
        x="year",
        y="employment",
        color="method_label",
        title=f"{selected_occ}: Employment forecast",
        markers=True,
        labels={"employment": "Employment", "year": "Year", "method_label": "Methodology"},
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Methodology snapshot")
    compare_years = [df["year"].min(), 2030]
    snapshot = (
        occ_df[occ_df["year"].isin(compare_years)]
        .pivot_table(index="method_label", columns="year", values="employment")
        .rename(columns={compare_years[0]: f"Employment {compare_years[0]}", compare_years[1]: "Employment 2030"})
    )
    snapshot["Change"] = snapshot["Employment 2030"] - snapshot[f"Employment {compare_years[0]}"]
    snapshot["% Change"] = np.where(
        snapshot[f"Employment {compare_years[0]}"] > 0,
        snapshot["Change"] / snapshot[f"Employment {compare_years[0]}"] * 100,
        np.nan,
    )
    snapshot = snapshot.sort_values("Change", ascending=False)
    snapshot["Change"] = snapshot["Change"].apply(format_number)
    snapshot["% Change"] = snapshot["% Change"].apply(lambda v: f"{v:.1f}%" if not np.isnan(v) else "-")
    st.dataframe(snapshot, use_container_width=True)

    st.markdown("### Occupation table")
    label_to_method = {label_map[m]: m for m in selected_methods}
    method_label_options = list(label_to_method.keys())
    default_label = label_map.get(selected_methods[0], method_label_options[0])
    selected_label = st.selectbox(
        "Table methodology",
        options=method_label_options,
        index=method_label_options.index(default_label) if default_label in method_label_options else 0,
    )
    table_method = label_to_method[selected_label]
    table_df = df[df["methodology"] == table_method].copy()

    segment_options = (
        table_df[table_df["segment_id"] != 0][["segment_id", "segment_name"]]
        .drop_duplicates()
        .sort_values("segment_id")
        .assign(label=lambda d: d["segment_id"].astype(str) + " - " + d["segment_name"])
    )
    selected_segments = st.multiselect(
        "Filter segments",
        options=segment_options["label"].tolist(),
        default=segment_options["label"].tolist(),
        help="Limit the table to specific supply segments (defaults to all).",
    )
    if selected_segments:
        segment_ids = {int(label.split(" - ")[0]) for label in selected_segments}
        table_df = table_df[table_df["segment_id"].isin(segment_ids)]

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
        st.info("No occupations match the selected filters.")
        return

    pivot = (
        table_df.pivot_table(index=["occcd", "soctitle"], columns="year", values="employment")
        .reindex(sorted(table_df["year"].unique()), axis=1)
        .fillna(0.0)
    )
    pivot["Change"] = pivot.iloc[:, -1] - pivot.iloc[:, 0]
    pivot["% Change"] = np.where(pivot.iloc[:, 0] > 0, pivot["Change"] / pivot.iloc[:, 0] * 100, np.nan)
    pivot = pivot.sort_values("Change", ascending=False)
    pivot["Change"] = pivot["Change"].apply(format_number)
    pivot["% Change"] = pivot["% Change"].apply(lambda v: f"{v:.1f}%" if not np.isnan(v) else "-")
    st.dataframe(pivot, use_container_width=True)


def layout_supply_chain(naics_df: pd.DataFrame) -> None:
    st.subheader("Supply Chain Structure (2024 Baseline)")
    st.markdown(
        """
        Auto-adjusted employment is derived by applying SAM shares at the NAICS level.
        The table below summarises 2024 QCEW employment alongside the share applied
        to estimate automotive-linked employment.
        """
    )
    table = naics_df.copy()
    table["Raw Employment 2024"] = table["employment_raw"].apply(format_number)
    table["Auto Employment 2024"] = table["employment_auto"].apply(format_number)
    table["Auto Share"] = table["share_applied"].apply(lambda v: f"{v:.1%}")
    display_cols = [
        "segment_id",
        "segment_name",
        "stage",
        "naics_code",
        "naics_title",
        "Raw Employment 2024",
        "Auto Employment 2024",
        "Auto Share",
    ]
    st.dataframe(
        table[display_cols].rename(
            columns={
                "segment_id": "Segment ID",
                "segment_name": "Segment",
                "stage": "Stage",
                "naics_code": "NAICS",
                "naics_title": "NAICS Title",
            }
        ),
        use_container_width=True,
    )


def layout_data_access(
    occ_df: pd.DataFrame,
    segment_ts: pd.DataFrame,
    stage_ts: pd.DataFrame,
) -> None:
    st.subheader("Data Access & Notes")
    st.markdown(
        textwrap.dedent(
            """
            - **Occupation detail**: `data/processed/sam_auto_dashboard/sam_occ_segment_totals_2024_2034.csv`
            - **Segment time series**: `data/processed/sam_auto_dashboard/sam_employment_segment_timeseries.csv`
            - **Stage time series**: `data/processed/sam_auto_dashboard/sam_employment_stage_timeseries.csv`
            - **Pipeline**: `scripts/build_sam_standard_dashboard_data.py`
            """
        )
    )

    st.markdown("#### Preview (occupation forecasts)")
    st.dataframe(occ_df.head(), use_container_width=True)
    st.download_button(
        "Download occupation data (CSV)",
        data=occ_df.to_csv(index=False).encode("utf-8"),
        file_name="sam_occ_segment_totals_2024_2034.csv",
        mime="text/csv",
    )

    st.markdown("#### Preview (segment employment)")
    st.dataframe(segment_ts.head(), use_container_width=True)
    st.download_button(
        "Download segment time series (CSV)",
        data=segment_ts.to_csv(index=False).encode("utf-8"),
        file_name="sam_employment_segment_timeseries.csv",
        mime="text/csv",
    )

    st.markdown("#### Preview (stage employment)")
    st.dataframe(stage_ts.head(), use_container_width=True)
    st.download_button(
        "Download stage time series (CSV)",
        data=stage_ts.to_csv(index=False).encode("utf-8"),
        file_name="sam_employment_stage_timeseries.csv",
        mime="text/csv",
    )


# --- Streamlit App ---
st.set_page_config(page_title="SAM-Based Automotive Employment Dashboard", layout="wide")

st.title("Michigan Automotive Employment ï¿½?ï¿½ SAM Standard")
st.caption(
    "Interactive exploration of SAM-adjusted employment projections (2024-2034) and occupation implications across projection scenarios."
)

forecasts = load_forecasts()
stage_series = load_stage_series()
segment_series = load_segment_timeseries()
naics_baseline = load_naics_baseline()

all_years = sorted(forecasts["year"].unique())
all_methods = sorted(forecasts["methodology"].unique())
label_map = {method: methodology_display(method) for method in all_methods}
selected_methods = build_methodology_selector(all_methods, label_map)
filtered_forecasts = forecasts[forecasts["methodology"].isin(selected_methods)].copy()

overview_tab, segment_tab, stage_tab, occupation_tab, supply_tab, data_tab = st.tabs(
    [
        "Overview",
        "Segments",
        "Stage / Horizon",
        "Occupation Explorer",
        "Supply Chain",
        "Data & Notes",
    ]
)

with overview_tab:
    layout_overview(filtered_forecasts, selected_methods)

with segment_tab:
    layout_segments(filtered_forecasts, selected_methods, all_years)

with stage_tab:
    layout_stage_trends(stage_series, selected_methods)

with occupation_tab:
    layout_occupation_insights(filtered_forecasts, selected_methods, label_map)

with supply_tab:
    layout_supply_chain(naics_baseline)

with data_tab:
    stage_methods = {f"sam_mi_{projection_slug(m)}" for m in selected_methods}
    layout_data_access(
        filtered_forecasts,
        segment_series[segment_series["methodology"].isin(selected_methods)],
        stage_series[stage_series["methodology"].isin(stage_methods)],
    )
