# Occupation-Level Forecast Methodology

## Overview

This document describes the methodology for generating occupation-level employment forecasts for Michigan's automotive supply chain segments from 2024 through 2034, with particular emphasis on 2030 projections for workforce planning.

## Analytical Framework

### Three-Step Methodology

The occupation forecasting approach combines three distinct analytical steps, each addressing a specific dimension of workforce projection:

```
┌─────────────────────────────────────┐
│ Step 1: Auto Attribution Adjustment │
│                                     │
│ MCDA 2024 Staffing × Auto Share    │
│ = Auto-Specific Occupational Mix   │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ Step 2: Segment Growth Application │
│                                     │
│ Auto Occupation Mix ×               │
│ Segment Employment Forecast =      │
│ Scaled Occupation Employment        │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│ Step 3: Occupational Shift         │
│                                     │
│ Apply BLS 2024-2034 Share Changes  │
│ = Final Occupation Forecast         │
└─────────────────────────────────────┘
```

---

## Step 1: Auto Attribution Adjustment

### Objective
Isolate the automotive-specific portion of 2024 MCDA staffing patterns by discounting employment in industries that serve both automotive and non-automotive markets.

### Data Inputs
- **MCDA 2024 Staffing Patterns** (`data/interim/mcda_staffing_long_2021_2024.csv`)
  - Occupation-level employment by segment for 2024
  - Based on Michigan OEWS data aggregated to 10 automotive segments

- **BEA Auto Attribution Shares** (`data/raw/auto_attribution_bea.csv`)
  - Defines proportion of each NAICS code attributable to automotive sector
  - Based on Bureau of Economic Analysis industry definitions

- **Lightcast Auto Attribution Shares** (`data/raw/auto_attribution_core_auto_lightcast.csv`)
  - Alternative definition from Lightcast Core Auto research
  - Industry-specific research on automotive exposure

### Methodology

1. **Compute Segment-Level Auto Shares**:
   - For each segment, calculate employment-weighted average auto share across constituent NAICS codes
   - Formula: `segment_auto_share = Σ(naics_employment × naics_auto_share) / Σ(naics_employment)`

2. **Apply to Occupational Employment**:
   - For each occupation within each segment:
   - `auto_occupation_employment = mcda_employment × segment_auto_share`
   - Maintains proportional occupational mix (assumes auto and non-auto portions have similar staffing)

3. **Preserve Both Attribution Approaches**:
   - Generate separate datasets for BEA and Lightcast attributions
   - Enables sensitivity analysis on attribution methodology choice

### Key Assumption
**Occupational mix is similar between auto and non-auto portions of each industry**. For example, if NAICS 3261 (Plastics Manufacturing) is 31% automotive, we assume the occupational distribution is similar in the automotive 31% as in the total industry.

**Limitation**: May not hold for highly specialized industries where auto work requires different skill sets. However, data constraints prevent more granular estimation.

### Example Calculation

Segment 1 (Materials & Processing):
- NAICS 3261: Employment = 34,371, BEA Share = 0.608, Lightcast Share = 0.310
- NAICS 3262: Employment = 5,147, BEA Share = 0.608, Lightcast Share = 0.670
- ...additional NAICS codes

Weighted BEA Share = (34,371 × 0.608 + 5,147 × 0.608 + ...) / 72,030 = 0.45
Weighted Lightcast Share = (34,371 × 0.310 + 5,147 × 0.670 + ...) / 72,030 = 0.38

For SOC 51-4041 (Machinists) with 2024 MCDA employment = 1,200:
- BEA-adjusted employment = 1,200 × 0.45 = 540
- Lightcast-adjusted employment = 1,200 × 0.38 = 456

---

## Step 2: Segment Growth Application

### Objective
Scale auto-specific occupational employment from 2024 through 2034 using segment-level employment forecasts.

### Data Inputs
- **Segment Employment Forecasts** (4 files in `data/processed/`):
  - `mi_qcew_segment_employment_timeseries_bea_extended_moody.csv` - BEA attribution, Moody's growth
  - `mi_qcew_segment_employment_timeseries_bea_extended_bls.csv` - BEA attribution, BLS growth
  - `mi_qcew_segment_employment_timeseries_coreauto_extended_moody.csv` - Lightcast attribution, Moody's growth
  - `mi_qcew_segment_employment_timeseries_coreauto_extended_bls.csv` - Lightcast attribution, BLS growth

### Methodology

1. **Match Attribution Approaches**:
   - BEA-adjusted occupations use BEA segment forecasts
   - Lightcast-adjusted occupations use Lightcast segment forecasts

2. **Apply Segment Growth**:
   - For each occupation-segment-year combination:
   - Retrieve segment total employment for that year
   - Without Step 3 adjustments: `occupation_employment_year = base_2024_employment × (segment_employment_year / segment_employment_2024)`

3. **Preserve Methodology Combinations**:
   - 2 attribution approaches × 2 growth sources = 4 forecast scenarios
   - Enables sensitivity analysis on both attribution and growth rate assumptions

### Example Calculation

Continuing the Machinists example:

Segment 1 forecast (BEA × Moody's):
- 2024: 32,000 total employment
- 2030: 29,500 total employment (7.8% decline)

Machinists forecast (BEA × Moody's), without occupational shift:
- 2030: 540 × (29,500 / 32,000) = 498

---

## Step 3: Occupational Shift Incorporation

### Objective
Account for changing occupational composition within segments over time (e.g., increasing engineers, declining production workers).

### Data Inputs
- **BLS Industry×Occupation Matrices** (`data/raw/us_staffing_patterns/*.csv`)
  - Occupation shares within each NAICS code for 2024 and 2034
  - From BLS Employment Projections Table 1.9
  - Detailed (6-digit SOC) occupational granularity

### Methodology

1. **Compile BLS Occupational Shares**:
   - For each NAICS code in segment framework:
   - Extract "2024 Percent of Industry" and "Projected 2034 Percent of Industry" for each occupation
   - Aggregate to segment level using QCEW employment weights

2. **Interpolate Intermediate Years**:
   - Linear interpolation between 2024 and 2034 shares
   - Formula for year t: `share(t) = share_2024 + (share_2034 - share_2024) × ((t - 2024) / 10)`

3. **Apply Occupational Shares**:
   - For each occupation-segment-year:
   - `occupation_employment = segment_employment × bls_share(year)`
   - Overrides constant-share assumption from Step 2

4. **Fallback Logic**:
   - If BLS data unavailable for occupation-NAICS pair: maintain 2024 share constant
   - Tracks which occupations have BLS shift data vs. constant share (`has_bls_shift` flag)

### Key Assumption
**BLS national occupational trends apply to Michigan automotive segments**. Michigan's shift from production to engineering roles may differ from US averages, but lack of MI-specific projections necessitates this assumption.

### Example Calculation

Machinists in Segment 1:
- BLS 2024 share: 1.75% of segment employment
- BLS 2034 share: 1.50% of segment employment (declining due to automation)

For 2030 (6 years into 10-year projection):
- Interpolated share = 1.75% + (1.50% - 1.75%) × (6/10) = 1.60%

Segment 1 total employment (BEA × Moody's) in 2030: 29,500

Machinists 2030 forecast (final):
- 29,500 × 0.0160 = 472 (vs. 498 without occupational shift adjustment)

---

## Methodology Combinations

The analysis produces **4 distinct forecast scenarios**:

| Scenario | Attribution | Growth Source | Use Case |
|----------|-------------|---------------|----------|
| **BEA × Moody's** | BEA auto shares | Moody's sector forecasts | Government definition, macro trends |
| **BEA × BLS** | BEA auto shares | BLS industry projections | Government definition, detailed industry |
| **Lightcast × Moody's** | Lightcast Core Auto | Moody's sector forecasts | Commercial research, macro trends |
| **Lightcast × BLS** | Lightcast Core Auto | BLS industry projections | Commercial research, detailed industry |

This 2×2 matrix enables sensitivity analysis on:
1. **Auto attribution uncertainty**: How sensitive are results to different definitions of "automotive industry"?
2. **Growth rate uncertainty**: Do Moody's macro trends differ from BLS detailed projections?

---

## Key Outputs

### Primary Datasets

1. **Full Time Series** (`mi_occupation_employment_forecasts_2024_2034.csv`)
   - Every occupation × segment × year × methodology combination
   - Columns: `segment_id`, `segment_name`, `occupation_code`, `occupation_title`, `year`, `employment`, `attribution`, `growth_source`, `methodology`, `has_bls_shift`

2. **2030 Snapshot** (`mi_occupation_employment_forecast_2030.csv`)
   - Filtered to year 2030 (priority for workforce planning)
   - Same structure as full time series

3. **2030 Summary Report** (`mi_occupation_2030_summary_report.csv`)
   - Occupation-level aggregation across methodologies
   - Columns: `occupation_code`, `occupation_title`, `min_employment`, `max_employment`, `avg_employment`, `std_employment`, `segment_name`
   - Shows methodology spread for each occupation

### Separate by Attribution

- **BEA Forecasts** (`mi_occupation_employment_forecasts_bea_2024_2034.csv`)
- **Lightcast Forecasts** (`mi_occupation_employment_forecasts_lightcast_2024_2034.csv`)

---

## Data Quality & Limitations

### BLS Occupational Shift Coverage
- **BLS data available**: ~60-70% of occupation-segment pairs
- **Constant share fallback**: Remaining 30-40% use 2024 share through 2034
- **Impact**: Underestimates occupational change in segments/occupations without BLS data

### Attribution Assumptions
- **Same occupational mix**: Assumes auto and non-auto portions have similar staffing
- **Reality**: May vary (e.g., auto plastics might have more quality inspectors than food packaging plastics)
- **Mitigation**: Two attribution approaches provide bounds

### National vs. Michigan Trends
- **BLS projections**: Based on US national industry trends
- **Michigan reality**: State-specific factors (policy, major plant closures, supplier concentration) not captured
- **Mitigation**: Segment-level Michigan forecasts (Step 2) localize the analysis

### Temporal Interpolation
- **Linear assumption**: Occupational share changes assumed linear 2024-2034
- **Reality**: May be non-linear (e.g., sudden automation events, regulatory changes)
- **Impact**: Mid-decade projections (2027-2030) most affected

### Out-of-Scope Factors
This methodology does **not** explicitly model:
- Occupational migration patterns (workers moving in/out of state)
- Retirement and demographic effects
- Educational pipeline constraints (engineering program capacity)
- Skill upgrading within occupations (e.g., machinists learning CNC programming)
- Firm-specific workforce strategies

These factors should be considered when interpreting results for policy decisions.

---

## Validation & Quality Checks

### Internal Consistency Checks
1. **Occupation totals sum to segment totals** (within rounding tolerance)
2. **2024 base year matches MCDA × auto share** for each methodology
3. **Methodology spread is reasonable** (typically 5-15% range for 2030)

### External Validation
Recommended comparisons:
1. **Segment 7 (Core Automotive)** 2030 forecast vs. OEM announced capacity plans
2. **Engineering occupations** growth vs. electrification workforce needs literature
3. **Production occupations** decline vs. automation adoption rates in auto manufacturing

### Plausibility Heuristics
- Total 2030 employment should be within ±20% of 2024 (extreme scenarios only)
- No single occupation should dominate segment (>40% share)
- Top 5 occupations should account for 30-50% of segment employment
- Growth/decline rates should align with segment trends (not opposite direction)

---

## Usage Guidelines

### For Workforce Planning
- **Focus on 2030 snapshot** for near-term planning horizon
- **Use average across methodologies** as central estimate
- **Use min/max range** for scenario planning
- **Flag occupations with large methodology spread** for additional research

### For Policy Analysis
- **Compare BEA vs. Lightcast** to assess sensitivity to auto definition
- **Examine occupations with vs. without BLS shift data** to identify data gaps
- **Track top growing/declining occupations** for training program targeting

### For Stakeholder Communication
- **Lead with 2030 average estimates** (single number for clarity)
- **Show methodology range** (min-max) to convey uncertainty
- **Highlight top 10-15 occupations** by employment or growth
- **Explain Step 1-2-3 logic** in non-technical language

---

## Technical Implementation

### Script
`scripts/create_occupation_forecasts.py`

**Runtime**: ~2-5 minutes (depending on system)

**Dependencies**: pandas, numpy

**Inputs** (read from `data/` subdirectories):
- MCDA staffing patterns
- Attribution shares (BEA and Lightcast)
- Segment forecasts (4 files)
- BLS occupational shift data (30+ files)
- Segment assignments lookup

**Outputs** (written to `data/processed/`):
- 3 main CSV files
- 2 attribution-specific CSV files
- 1 summary statistics file

### Notebook
`notebooks/14_occupation_forecasts.ipynb`

**Purpose**: Interactive analysis, visualization, and quality checks

**Sections**:
1. Load and preview forecast data
2. Top occupations analysis (2030)
3. Growth/decline analysis (2024-2030)
4. Segment-level aggregations
5. Methodology comparison
6. Time series visualizations
7. Occupational shift impact
8. Export summary report

---

## References

### Data Sources
- **MCDA Staffing Patterns**: Michigan Center for Data and Analytics, derived from BLS OEWS
- **BLS Employment Projections**: 2024-2034 projections, released 2024
- **BEA Attribution**: Bureau of Economic Analysis auto industry definitions
- **Lightcast Attribution**: Core Auto research, industry-specific exposure analysis

### Methodological Precedents
This approach adapts techniques from:
- BLS Employment Projections methodology (occupational staffing patterns)
- Regional economic impact modeling (industry-specific employment multipliers)
- Workforce development planning (occupation-level forecasting for training programs)

### Related Documentation
- [methodology.md](methodology.md) - Decision log with dated entries
- [data_sources.md](data_sources.md) - Full data provenance
- [../notebooks/README.md](../notebooks/README.md) - Notebook 14 description
- [../scripts/README.md](../scripts/README.md) - Script documentation (to be created)

---

## Updates & Revisions

**Version 1.0** (2025-10-02): Initial methodology documentation

Future revisions should note:
- Changes to attribution approaches
- New data sources added
- Methodological refinements
- Validation findings that necessitate adjustments

---

**For questions about this methodology**:
1. Review executed notebook `14_occupation_forecasts_executed.ipynb` for worked examples
2. Examine script comments in `create_occupation_forecasts.py` for implementation details
3. Check methodology decision log in `methodology.md` for context on choices made
