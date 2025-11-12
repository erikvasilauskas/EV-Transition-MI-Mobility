# Appendix Y. Employment Projection and Occupational Forecast Methods

This appendix documents the workflow used to derive the SAM-standard
employment projections and occupation metrics that populate the updated
dashboard. It references the repository structure for reproducibility
and describes the analytical intent behind each processing stage.

## Overview

The SAM-based employment pipeline combines three main inputs:

1. **Automotive attribution shares** from the Michigan Social Accounting
   Matrix (SAM) processed via
   `scripts/build_sam_auto_shares_v2.py` and stored in
   `data/intermediate/sam_naics_shares_v2/sam_auto_naics4_mobility38.csv`.
2. **Growth rates** for multiple projection scenarios pulled from
   `data/raw/naics-level-employment-projections.csv` and normalized by
   `scripts/build_employment_projection_comparison.py`, producing
   `data/intermediate/employment_projection_comparison.csv`.
3. **Segment-to-occupation staffing shares** drawn from MCDA/Lightcast
   files in `data/processed/mcda_staffing_detailed_2021_2024.csv`.
4. **BLS occupational drift factors** derived from Employment Projections
   Table 1.9 detail files, aggregated to segments in
   `data/processed/us_staffing_segments_summary.csv`.

The script `scripts/build_sam_standard_dashboard_data.py` orchestrates
the full process. It applies SAM-derived shares to baseline employment,
projects forward under several growth scenarios, and distributes segment
totals to occupations. All outputs are written to
`data/processed/sam_auto_dashboard/` for consumption by updated
dashboards and notebooks.

## Step-by-Step Workflow

### 1. Load SAM Shares and Projection Rates

* File: `data/intermediate/sam_naics_shares_v2/sam_auto_naics4_mobility38.csv`
* Purpose: provides NAICS-level `auto_share_of_output` along with the
  mobility segment and stage assignments. Only upstream industries
  (stage = “Upstream”) plus NAICS 5413, 5414, and 5417 are adjusted; all
  other NAICS retain their full 2024 QCEW employment.

* File: `data/intermediate/employment_projection_comparison.csv`
* Purpose: supplies Moody’s Michigan/US, DTMB, and BLS employment change
  rates for each NAICS industry.

The merged dataset is the basis for all subsequent calculations. For
each NAICS, the script stores:

```text
auto_share_applied = auto_share_of_output if stage == "Upstream"
                    or naics_code in {5413, 5414, 5417}
                    else 1.0

auto_base_employment = employment_qcew_2024 * auto_share_applied
```

### 2. Build NAICS Time Series

Using the annualized variants of the six-year growth rates, the script
creates a time series from 2024 through 2034 for each projection method
(Moody’s MI, Moody’s US, DTMB MI, BLS US). All four scenarios share the
same SAM-derived baseline; they diverge only due to projection rates.

Output:
`data/processed/sam_auto_dashboard/sam_employment_naics_timeseries.csv`
with distinct columns for raw employment, auto-adjusted employment,
rate/cagr metadata, and the applied share.

Analytical intent: track how much of each industry’s employment is
treated as automotive, and allow downstream comparisons across
projection scenarios.

### 3. Aggregate to Segments and Stages

The NAICS time series roll up to segment- and stage-level files:

* `sam_employment_segment_timeseries.csv` – totals by segment and
  projection method. Includes `adjustment_source=sam_mi` and the
  calculated auto share ratio (auto employment ÷ raw employment).
* `sam_employment_stage_timeseries.csv` – similar aggregation by
  production stage, plus an `Upstream+Core` combined row.

These tables represent the input panels for segment/stage visualizations.

### 4. Prepare Occupation Forecast Inputs

The script loads detailed staffing shares from
`data/processed/mcda_staffing_detailed_2021_2024.csv` and retains the
2024 proportional distribution of occupations within each segment.
The BLS staffing table provides 2024 and 2034 shares for each occupation
within every mobility segment. For each occupation-segment pair the
script computes an annualised drift factor, applies it to the Michigan
baseline share, and normalises the resulting shares so they continue to
sum to one within each segment-year. Segment employment totals from each
projection scenario are then multiplied by the drift-adjusted shares to
obtain both `employment_auto` (SAM-adjusted) and `employment_raw`
estimates. Baseline openings from the MCDA data are scaled in proportion
to `employment_auto` so that occupation-level openings track the
auto-attributed job counts.

Outputs:

| File | Description |
| --- | --- |
| `sam_occ_segment_totals_2024_2034.csv` | Complete SOC-level panel by segment, method, and year (includes `employment_auto`, `employment_raw`, and legacy `employment` = auto). |
| `sam_occ_segment_totals_2030.csv` | Snapshot for 2030 only (useful for quick reporting). |
| `sam_occ_segment_totals_validation.csv` | Check that segment-level sums match `sam_employment_segment_timeseries.csv`. |

### 5. Summary of Repository Artifacts

*Processing scripts* (under `scripts/`):

- `build_sam_auto_shares_v2.py` – generate SAM attribution shares from
  raw Michigan SAM data.
- `build_employment_projection_comparison.py` – normalize the raw growth
  rate file.
- `build_sam_standard_dashboard_data.py` – the integrated workflow that
  creates SAM-adjusted projections and occupation outputs.

*Key intermediate data* (under `data/intermediate/`):

- `sam_naics_shares_v2/sam_auto_naics4_mobility38.csv` – NAICS-level SAM
  shares.
- `employment_projection_comparison.csv` – cleaned projection rates.

*Processed deliverables* (under `data/processed/sam_auto_dashboard/`):

- `sam_employment_naics_timeseries.csv`
- `sam_employment_segment_timeseries.csv`
- `sam_employment_stage_timeseries.csv`
- `sam_segment_totals_for_occ.csv` (segment totals in the format required
  by other tooling)
- `sam_occ_segment_totals_2024_2034.csv`
- `sam_occ_segment_totals_2030.csv`
- `sam_occ_segment_totals_validation.csv`

## Analytical Purpose

The SAM-standard workflow formalizes how much of each industry’s
employment is considered part of the automotive supply chain. By
restricting the adjustment to upstream industries and specific OEM
support NAICS (5413, 5414, 5417), the method isolates the portion of
employment that most plausibly scales with vehicle production and
supplier demand. Segment and stage aggregations allow stakeholders to
compare scenarios across the mobility value chain, while the occupation
outputs translate segment-level swings into potential workforce impacts.

These files feed the new dashboard revision, enabling consistent
comparisons across projection sources while anchoring the analysis in
the Michigan SAM as the chosen standard for industry attribution.

## NAICS → Segment → Occupation Narrative

1. **NAICS-level growth**
   - Baseline: 2024 Michigan QCEW jobs for each NAICS code.
   - Adjustment: multiply by the SAM `auto_share_of_output` (restricted to upstream NAICS plus 5413/5414/5417) to obtain `employment_auto` while keeping the unadjusted `employment_raw`.
   - Projection: apply the four sets of six-year growth rates (Moody's MI, Moody's US, DTMB MI, BLS US) that have been annualized to build 2024–2034 time series in `sam_employment_naics_timeseries.csv`. The SAM share is held constant across scenarios; only the growth trajectory differs.

2. **Segment rollups**
   - Each NAICS row carries a segment and stage assignment from `sam_auto_naics4_mobility38.csv`.
   - For every projection scenario and year we sum NAICS records to segments (`sam_employment_segment_timeseries.csv`) and stages (`sam_employment_stage_timeseries.csv`) while preserving both `employment_raw` and `employment_auto`.
   - These tables therefore show how industry-specific growth accumulates into the ten mobility segments (plus the Upstream+Core composite) under each forecast source.

3. **Occupation detail inside each segment**
   - MCDA staffing patterns supply the 2024 Michigan share for each SOC within a segment.
   - BLS Employment Projections (2024 base, 2034 target) provide a national staffing share for the same SOC/segment pair. We convert the 2024→2034 change into an annualized drift factor.
   - For every projection scenario and year we (a) evolve the MCDA share using the drift factor, (b) re-normalize shares so they sum to 1.0 within the segment, and (c) multiply by the segment's `employment_auto` (and `employment_raw`) to obtain occupation counts.
   - This produces `sam_occ_segment_totals_2024_2034.csv`, where `employment_auto` reflects both the SAM attribution and the BLS-informed compositional drift, while `employment_raw` shows the un-attributed counterpart. Occupational openings are scaled from the MCDA baseline in proportion to the updated `employment_auto`.

In short, NAICS growth rates drive segment totals; SAM shares determine how much of each industry is considered automotive; and BLS drift plus MCDA staffing patterns control how those segment totals distribute to occupations year by year.
