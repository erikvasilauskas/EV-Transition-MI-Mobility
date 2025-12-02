# Q1 2025 SAM Auto Dashboard Outputs

This directory stores the canonical outputs for the “Q1 2025” refresh of the Michigan SAM auto dashboard. The files here are overwritten each time the builder is rerun, so treat this folder as an artifact dump rather than a source of truth for manual edits.

## Source scripts

| Script | Purpose |
| --- | --- |
| `scripts/build_sam_dashboard_2025_Q1.py` | End-to-end builder. Reads the March 2025 QCEW baseline, applies SAM auto shares and the four projection sources (Moody’s MI + US, DTMB MI, BLS US) plus the Moody’s Michigan detailed multipliers, then writes NAICS/segment/stage time series, occupation totals, and validation tables into this directory. |
| `scripts/export_q1_segment_stage_plots.py` | Consumes `sam_employment_segment_timeseries.csv` and `sam_employment_stage_timeseries.csv` to produce historical + projection plots (PNG) by segment and stage. It stitches together the monthly QCEW history (Jan 2000–Mar 2025) with the annual projections (2026–2030) and drops the images under `plots_q1/`. |
| `scripts/export_q1_projection_tables.py` | Builds the custom comparison tables in `custom_table_output/segment_stage_projection_change.xlsx`, listing 2025 employment and the 2025→2030 level deltas for Moody’s MI detail, Moody’s MI CAGR, BLS US, and DTMB MI at both the segment and stage levels. |
| `scripts/export_q1_bls_segment7_occ_tables.py` | Creates `custom_table_output/bls_segment7_occ_highlights.xlsx`, which ranks Core Automotive (segment 7) occupations under the BLS US scenario by level change, percent change, and share change (both increasing and declining). Metadata fields (education, training, wages, openings, etc.) are preserved in every tab. |
| `scripts/export_q1_stage_group_occ_tables.py` | Generates occupation highlight workbooks for each projection scenario (Moody’s MI detail, Moody’s MI, Moody’s US, BLS US, DTMB MI). For every stage grouping (Upstream, Core/OEM, Downstream, Upstream + Core/OEM), the script writes an Excel file inside `custom_table_output/<scenario_slug>/` with the same layout as the segment 7 highlights (level/percent change increases & declines plus share-change tabs, all with full metadata). |

Each exporter expects the builder outputs in their default locations; rerun the builder before exporting if any inputs change.

## Baseline note (optional)

The Q1 pipeline treats the March 2025 QCEW level as the entire 2025 baseline for all projection sources. This keeps the historical series monthly up to March and annual thereafter, but it understates the “full-year 2025” level for projection methods that assume growth continues through December. If tighter alignment with annual projections is required later, we can apply 8/12 of each source’s 2024→2025 growth rate before freezing the 2025 totals (effectively forecasting from March to December). For now, the builder retains the pure March baseline, and the potential adjustment is documented here should we need to revisit it.
