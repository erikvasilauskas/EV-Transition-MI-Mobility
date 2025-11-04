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
Those shares remain constant through 2034 (i.e., the pipeline does not
incorporate U.S. BLS drift in this SAM-standard version).

For each projection scenario, segment employment totals are multiplied
by the relevant share to obtain occupation-level employment estimates.
Baseline openings from the MCDA data are scaled in proportion to
employment changes so that occupation-level openings track the
projected job counts.

Outputs:

| File | Description |
| --- | --- |
| `sam_occ_segment_totals_2024_2034.csv` | Complete SOC-level panel by segment, method, and year. |
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
