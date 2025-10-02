# Data Directory

This directory implements a multi-tier data pipeline for the EV-Transition analysis project, organizing datasets from raw source files through intermediate transformations to analysis-ready outputs.

## Directory Structure

### raw/
**Unmodified source files** from external data providers. Never edit files in this folder directly.

#### Core Employment & Economic Data
- **MI-QCEW-38-NAICS-2001-2024.xlsx**: Michigan Quarterly Census of Employment and Wages
  - Annual employment counts by NAICS code (2001-2024)
  - Source: Michigan Department of Labor via BLS
  - **Primary use**: Historical employment baseline for all segment analyses

- **QCEW_MI_2024.csv**: 2024 Michigan QCEW employment snapshot
  - Used as weights in segment aggregations
  - Joined to `lookups/segment_assignments.csv`

- **Moody's Supply Chain Employment and Output 1970-2055.xlsx**: Long-range forecasts
  - Employment and GDP projections by automotive segment
  - Covers Michigan and US national
  - **Primary use**: Extending QCEW data beyond 2024 using Moody's growth rates

#### Occupational Data
- **Staffing Patterns for 10 Categories.xlsx**: MCDA segment staffing patterns
  - Occupational employment distributions (SOC codes) for 10 automotive segments
  - Years: 2015, 2018, 2021, 2024
  - Source: Michigan Center for Data and Analytics
  - **Primary use**: Identifying critical occupations within each segment

- **us_staffing_patterns/**: BLS industry×occupation matrices (2024-2034 projections)
  - Directory contains 30+ CSV files, one per NAICS code
  - Retrieved via [scripts/fetch_us_staffing.py](../scripts/fetch_us_staffing.py)
  - Source: BLS Employment Projections Table 1.9
  - **Primary use**: Benchmarking Michigan staffing patterns against US national

- **us_staffing_patterns_naics.csv**: List of NAICS codes in staffing patterns directory

#### BLS Employment Projections
- **occupation_2023_ep.xlsx**: BLS 2023 Employment Projections package
  - Contains multiple tables including Table 1.2 (occupational projections)
  - 2023 base year, 2033 projection horizon

- **occupation_2024_ep.xlsx**: BLS 2024 Employment Projections package
  - Contains multiple tables including Table 1.2 (occupational projections)
  - 2024 base year, 2034 projection horizon
  - **Primary use**: Year-over-year growth rates for extending QCEW

#### Attribution & Classification
- **auto_attribution_bea.csv**: BEA automotive industry attribution shares
  - Defines what portion of each NAICS code is "automotive"
  - Source: Bureau of Economic Analysis methodology
  - Used in BEA forecast scenario ([scripts/apply_bea_share_and_extend.py](../scripts/apply_bea_share_and_extend.py))

- **auto_attribution_core_auto_lightcast.csv**: Lightcast automotive attribution shares
  - Alternative auto-industry definition from Lightcast research
  - Used in Lightcast/Core Auto forecast scenario ([scripts/apply_lightcast_share_and_extend.py](../scripts/apply_lightcast_share_and_extend.py))

- **NAICS_sectors_August_18_2025.xlsx**: NAICS sector reference table
  - Industry titles and hierarchical structure
  - Used for joining human-readable names

### external/
**Reference datasets** used for joins, crosswalks, and validation. These are typically standard taxonomies or classification systems that don't change frequently.

Examples:
- NAICS code crosswalks (2007→2012→2017 revisions)
- SOC occupational taxonomy
- Geographic identifiers (FIPS codes, county names)

### lookups/
**Controlled vocabularies and mapping tables** that define the analytical framework.

#### segment_assignments.csv
The **authoritative mapping** of NAICS codes to 10 automotive supply-chain segments.

**Columns**:
- `naics_code`: 4-digit NAICS code
- `naics_title`: Industry description
- `segment_id`: Segment number (1-10)
- `segment_name`: Descriptive segment name
- `stage`: Supply chain stage (Upstream, OEM, Downstream)
- `employment_qcew_2024`: Michigan employment count from 2024 QCEW
- `mi_employment_pct_change_2024_2030`: Moody's projected employment % change
- `mi_wage_pct_change_2024_2030`: Moody's projected wage % change
- `mi_gdp_pct_change_2024_2030`: Moody's projected GDP % change

**Row count**: 38 NAICS codes (one row per code)

**Key characteristics**:
- Weighted aggregation: `employment_qcew_2024` used as weights when rolling up multi-industry segments
- Enriched with Moody's: Projection deltas enable forecast comparisons
- Stage hierarchy: Enables 3-tier rollups (Upstream/OEM/Downstream)

**Update frequency**: As needed when segment definitions change or QCEW data refreshes

### interim/
**Cleaned and transformed datasets** ready for aggregation. These files represent intermediate outputs from ETL scripts.

#### Time Series Data
- **mi_qcew_naics_*_timeseries.csv**: NAICS-level time series (2001-2024 historical)
  - `_employment`: Employment counts
  - `_bea`: BEA-attributed auto-specific employment
  - `_coreauto`: Lightcast-attributed auto-specific employment

- **mi_qcew_segment_employment_timeseries*.csv**: Segment-level aggregations (2001-2024)
  - Base version: Direct QCEW rollup by segment
  - `_bea`: Using BEA attribution
  - `_coreauto`: Using Lightcast attribution

- **mi_qcew_stage_employment_timeseries*.csv**: Stage-level aggregations (2001-2024)
  - Upstream, OEM, Downstream rollups
  - Variants for each attribution approach

#### Growth Rates & Projections
- **bls_us_segments_timeseries_yoy.csv**: BLS year-over-year growth by segment (US national)
- **bls_us_stages_timeseries_yoy.csv**: BLS year-over-year growth by stage (US national)
- **moodys_michigan_segments_timeseries*.csv**: Moody's Michigan projections by segment
  - Base version: Employment time series (1970-2055)
  - `_yoy`: Year-over-year growth rates
- **moodys_us_segments_timeseries*.csv**: Moody's US national projections by segment

#### Diagnostic Files
- **mi_qcew_segment_*_diagnostics.csv**: Validation outputs from attribution scripts
  - Compare BEA vs. Lightcast vs. direct QCEW
  - Identify segments with large attribution differences
- **mi_qcew_stage_*_diagnostics.csv**: Stage-level diagnostic comparisons

#### Staffing Pattern Data
- **mcda_staffing_wide_2021_2024.csv**: MCDA staffing patterns in wide format
- **mcda_staffing_long_2021_2024.csv**: MCDA staffing patterns in long/tidy format
- **us_staffing_segments_long_2024_2034.csv**: US benchmarking staffing patterns
- **occupation_table12_tidy.csv**: BLS Table 1.2 cleaned/normalized

### processed/
**Analysis-ready datasets** for visualization, reporting, and stakeholder sharing.

#### Complete Time Series (Historical + Projected)
All files extend from 2001-2034 (24 years historical + 10 years projected)

**Segment-Level Forecasts**:
- **mi_qcew_segment_employment_timeseries.csv**: Baseline forecast (Moody's+BLS direct)
- **mi_qcew_segment_employment_timeseries_bea_extended_*.csv**: BEA attribution approach
  - `_moody`: Extended using Moody's growth rates
  - `_bls`: Extended using BLS growth rates
  - `_compare`: Side-by-side comparison of Moody vs. BLS
- **mi_qcew_segment_employment_timeseries_coreauto_extended_*.csv**: Lightcast approach
  - Same structure as BEA files

**Stage-Level Forecasts**:
- **mi_qcew_stage_employment_timeseries*.csv**: Same structure as segment files
  - 3 stages instead of 10 segments
  - Aggregates segment forecasts using stage hierarchy

#### Cross-Methodology Comparisons
- **mi_qcew_segment_employment_timeseries_extended_compare.csv**:
  - Compares baseline vs. BEA vs. Lightcast for all segments
  - Shows divergence between methodologies

- **mi_qcew_segment_employment_timeseries_lightcast_vs_bea_compare.csv**:
  - Direct comparison of Lightcast and BEA attribution approaches
  - Highlights which segments are most sensitive to attribution choice

- **mi_qcew_stage_employment_timeseries_lightcast_vs_bea_compare.csv**:
  - Same comparison at stage level

#### Staffing Pattern Outputs
- **mcda_staffing_*.csv**: Processed Michigan staffing patterns
- **occupation_table12_comparison.*.csv**: BLS projection comparisons (2023 vs. 2024 releases)
- **us_mi_segment_comparison_*.csv**: Michigan vs. US staffing pattern share comparisons

## Data Pipeline Flow

```
┌──────────────┐
│  Raw Data    │  External sources (BLS, Moody's, MCDA)
└──────┬───────┘
       │
       │  [ETL Scripts: scripts/process_*.py]
       │
       v
┌──────────────┐
│   Interim    │  Cleaned, normalized, historical only
└──────┬───────┘
       │
       │  [Forecast Scripts: scripts/apply_*.py]
       │
       v
┌──────────────┐
│  Processed   │  Analysis-ready with projections
└──────┬───────┘
       │
       │  [Visualization: notebooks/*.ipynb]
       │
       v
┌──────────────┐
│   Reports    │  Publication-ready outputs
└──────────────┘
```

## Key Data Processing Scripts

Located in [scripts/](../scripts/) directory:

1. **process_mi_qcew_segments.py**: Transforms raw QCEW into segment time series
2. **process_moodys_time_series.py**: Standardizes Moody's projections
3. **apply_lightcast_share_and_extend.py**: Lightcast attribution + forecasting
4. **apply_bea_share_and_extend.py**: BEA attribution + forecasting
5. **apply_moodys_and_bls_growth_to_qcew.py**: Baseline Moody's+BLS forecasting
6. **compute_bls_growth_timeseries.py**: Calculates YoY growth from BLS projections
7. **build_lightcast_vs_bea_comparison.py**: Cross-methodology comparison tool

## File Naming Conventions

### Prefixes
- `mi_`: Michigan-specific data
- `us_`: US national data
- `bls_`: Bureau of Labor Statistics source
- `moodys_`: Moody's Analytics source
- `mcda_`: Michigan Center for Data & Analytics source

### Suffixes
- `_timeseries`: Time-indexed data (year as column/index)
- `_yoy`: Year-over-year growth rates
- `_extended`: Includes projected years beyond historical data
- `_compare`: Side-by-side comparisons of methodologies
- `_diagnostics`: Validation and quality checks
- `_wide`: One row per entity, years as columns
- `_long`: Tidy format, one row per entity-year observation

### Attribution Tags
- `_bea`: Uses BEA auto attribution shares
- `_coreauto` or `_lightcast`: Uses Lightcast auto attribution shares
- No tag: Direct QCEW or baseline Moody's methodology

## Data Quality & Caveats

### NAICS Code Changes
QCEW data spans 2001-2024, covering multiple NAICS revision cycles (2002, 2007, 2012, 2017). The BLS maintains backward compatibility, but some codes have been split, merged, or reclassified. Our segment assignments use 2017 NAICS definitions.

### Suppressed Values
BLS suppresses employment data in cells with <10 establishments or where a single employer dominates. Suppressed values are marked with "c" or "*" in source files. We handle these as missing data or estimate using adjacent years when necessary.

### Moody's Sector Mappings
Moody's uses proprietary sector classifications that don't align perfectly with NAICS. We've created mappings in [segment_assignments.csv](lookups/segment_assignments.csv), validated against 2024 QCEW actuals. Mismatches <5% are considered acceptable.

### Attribution Uncertainty
The "auto-specific" share of industries like 3261 (Plastics Manufacturing) is inherently ambiguous. Different methodologies (BEA vs. Lightcast) produce materially different estimates. We address this by running parallel forecasts and documenting sensitivity.

### Occupational Data Gaps
Not all NAICS codes in our segment framework have publicly available industry×occupation matrices. When 6-digit NAICS data is unavailable, we fall back to:
1. 5-digit NAICS parent
2. 4-digit NAICS parent
3. 3-digit NAICS subsector

Fallback cases are documented in comparison scripts.

## Data Refresh Procedures

### Annual QCEW Update (Every March)
1. Download updated MI QCEW from [BLS website] or MI Dept of Labor portal
2. Replace `raw/MI-QCEW-38-NAICS-20XX-20YY.xlsx` with new file
3. Update `raw/QCEW_MI_20YY.csv` with latest year snapshot
4. Re-run `scripts/process_mi_qcew_segments.py`
5. Regenerate all forecasts with updated historical baseline

### Biennial BLS Projections Update (Even years)
1. Download new Employment Projections release from BLS
2. Add `raw/occupation_20YY_ep.xlsx` to collection
3. Run `scripts/fetch_us_staffing.py` to retrieve updated Table 1.9 matrices
4. Re-run `scripts/compute_bls_growth_timeseries.py`
5. Refresh forecasts using BLS growth option

### Quarterly Moody's Update (Optional)
1. Export latest Moody's sector forecasts for Michigan and US
2. Replace `raw/Moody's Supply Chain Employment and Output YYYY-YYYY.xlsx`
3. Re-run `scripts/process_moodys_time_series.py`
4. Refresh Moody's-based forecast scenarios

### MCDA Staffing Update (On demand)
1. Request updated staffing pattern workbook from MCDA
2. Replace `raw/Staffing Patterns for 10 Categories.xlsx`
3. Re-run `scripts/process_mcda_staffing.py`
4. Update MI vs. US staffing comparisons

## Data Security & PII

**No personally identifying information (PII)** should be stored in this repository. All datasets are aggregated to industry or occupational level.

**Restricted data**: Moody's Analytics data is licensed and subject to redistribution restrictions. Do not share raw Moody's files outside authorized project team.

**Public data**: BLS QCEW, OEWS, and Employment Projections data are public domain and may be freely shared.

## Additional Resources

- **BLS QCEW Documentation**: https://www.bls.gov/cew/
- **BLS Employment Projections**: https://www.bls.gov/emp/
- **Moody's Analytics**: https://www.economy.com/ (subscription required)
- **NAICS Manual**: https://www.census.gov/naics/

For questions about specific datasets or processing decisions, see:
- [docs/data_sources.md](../docs/data_sources.md) for source details
- [docs/methodology.md](../docs/methodology.md) for analytical decisions
- [scripts/README.md](../scripts/README.md) for script documentation
