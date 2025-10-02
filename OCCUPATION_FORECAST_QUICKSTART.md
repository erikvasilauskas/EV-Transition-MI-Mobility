# Occupation Forecast Quick Start Guide

## Overview

This guide walks you through generating occupation-level employment forecasts for Michigan's automotive supply chain through 2034, with emphasis on 2030 projections.

## Prerequisites

✅ **Data files must be in place**:
- MCDA 2024 staffing patterns
- Segment employment forecasts (4 files: BEA/Lightcast × Moody/BLS)
- BLS occupational shift data (us_staffing_patterns directory)
- Attribution files (BEA and Lightcast)

✅ **Python environment**: pandas, numpy, pathlib

---

## Step 1: Validate Data (RECOMMENDED)

Before running the full occupation forecast, validate that all required data is available:

```bash
python scripts/test_occupation_forecast_data.py
```

**Expected output**:
```
================================================================================
OCCUPATION FORECAST DATA VALIDATION
================================================================================

[1/6] Checking MCDA data...
  ✓ MCDA 2024: 1,234 records
    Segments: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    Occupations: 456

[2/6] Checking segment assignments...
  ✓ Segment assignments: 38 NAICS codes
    Segments: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

[3/6] Checking attribution files...
  ✓ BEA attribution: 32 NAICS codes
  ✓ Lightcast attribution: 30 NAICS codes

[4/6] Checking segment forecasts...
  ✓ BEA_Moody: 110 records (2024-2034)
  ✓ BEA_BLS: 110 records (2024-2034)
  ✓ Lightcast_Moody: 110 records (2024-2034)
  ✓ Lightcast_BLS: 110 records (2024-2034)

[5/6] Checking BLS staffing patterns...
  ✓ BLS staffing files: 35 NAICS codes
    ✓ All required columns present

[6/6] Checking data alignment...
  ✓ MCDA and lookup segments match: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

  NAICS coverage:
    Segments: 38 codes
    BEA: 32/38 covered (84%)
    Lightcast: 30/38 covered (79%)

================================================================================
VALIDATION COMPLETE
================================================================================

If all checks passed, you can run create_occupation_forecasts.py
```

**If validation fails**: Check error messages for missing files or data gaps. Address issues before proceeding.

---

## Step 2: Run Occupation Forecast Script

```bash
python scripts/create_occupation_forecasts.py
```

**Run time**: Approximately 2-5 minutes depending on system.

**Expected output**:
```
================================================================================
OCCUPATION-LEVEL FORECAST GENERATION
================================================================================

[1/6] Loading core datasets...
  - Loaded MCDA 2024 staffing: 1,234 occupation-segment records
  - Loaded segment assignments: 38 NAICS codes
  - Loaded BEA attribution: 32 NAICS codes
  - Loaded Lightcast attribution: 30 NAICS codes
  - Loaded BEA_Moody forecast: 110 segment-year records
  - Loaded BEA_BLS forecast: 110 segment-year records
  - Loaded Lightcast_Moody forecast: 110 segment-year records
  - Loaded Lightcast_BLS forecast: 110 segment-year records

[2/6] Loading BLS occupational shift data...
  - Compiled BLS shifts: 2,345 segment-occupation pairs

[3/6] Adjusting MCDA staffing patterns by auto attribution...
  - Computed auto shares for 10 segments
  - BEA-adjusted employment: 123,456
  - Lightcast-adjusted employment: 98,765
  - Original MCDA employment: 234,567

[4/6] Generating occupation forecasts (2024-2034)...

  Processing: BEA_Moody
    - Generated 12,340 occupation-year forecasts

  Processing: BEA_BLS
    - Generated 12,340 occupation-year forecasts

  Processing: Lightcast_Moody
    - Generated 12,340 occupation-year forecasts

  Processing: Lightcast_BLS
    - Generated 12,340 occupation-year forecasts

  Total occupation forecasts: 49,360

[5/6] Saving outputs...
  - Saved: data/processed/mi_occupation_employment_forecasts_2024_2034.csv
  - Saved 2030 snapshot: data/processed/mi_occupation_employment_forecast_2030.csv
  - Saved BEA forecasts: data/processed/mi_occupation_employment_forecasts_bea_2024_2034.csv
  - Saved Lightcast forecasts: data/processed/mi_occupation_employment_forecasts_lightcast_2024_2034.csv
  - Saved 2030 segment summary: data/processed/mi_occupation_forecast_2030_segment_summary.csv

[6/6] Summary statistics...

Top 20 occupations by 2030 employment (avg across methodologies):
  51-2092  Team Assemblers: 12,345
  49-3023  Automotive Service Technicians and Mechanics: 8,901
  ...

2030 Employment by Segment (avg across methodologies):
  Segment 7: 123,456
  Segment 9: 98,765
  ...

================================================================================
OCCUPATION FORECAST GENERATION COMPLETE
================================================================================

Key outputs:
  - 49,360 total occupation-year-methodology forecasts
  - 12,340 occupation forecasts for 2030
  - 456 unique occupations
  - 10 segments
  - 4 methodology combinations (BEA/Lightcast × Moody/BLS)
  - Years: 2024-2034
```

---

## Step 3: Analyze Results in Notebook

Open the interactive analysis notebook:

```bash
jupyter notebook notebooks/14_occupation_forecasts.ipynb
```

Or if using JupyterLab:
```bash
jupyter lab notebooks/14_occupation_forecasts.ipynb
```

**Execute all cells** to generate:
- Top occupations by 2030 employment
- Fastest growing/declining occupations (2024-2030)
- Segment-level employment aggregations
- Methodology comparison charts
- Time series visualizations for key occupations
- 2030 summary report for stakeholders

**Key charts generated** (saved to `reports/figures/`):
- `occupation_top15_2030.png` - Bar chart of top 15 occupations
- `occupation_segment_employment_2030.png` - Employment by segment
- `occupation_methodology_comparison_2030.png` - Methodology comparison
- `occupation_top5_timeseries_2024_2034.png` - Time series for top 5 occupations

---

## Step 4: Review Key Outputs

### Full Time Series
**File**: `data/processed/mi_occupation_employment_forecasts_2024_2034.csv`

**Structure**:
```
segment_id, segment_name, occupation_code, occupation_title, year, employment,
attribution, growth_source, methodology, has_bls_shift
```

**Use for**: Time series analysis, trend identification, annual forecasts

---

### 2030 Snapshot
**File**: `data/processed/mi_occupation_employment_forecast_2030.csv`

**Structure**: Same as full time series, filtered to year 2030

**Use for**: Workforce planning, 2030-focused stakeholder presentations

---

### 2030 Summary Report
**File**: `data/processed/mi_occupation_2030_summary_report.csv`

**Structure**:
```
occupation_code, occupation_title, min_employment, max_employment,
avg_employment, std_employment, segment_name
```

**Use for**:
- Executive summaries
- Highlighting methodology uncertainty (min/max range)
- Prioritizing occupations for workforce interventions

**Example**:
| Occupation | Min | Max | Avg | Std | Segment |
|------------|-----|-----|-----|-----|---------|
| 51-2092 Team Assemblers | 11,200 | 13,500 | 12,345 | 850 | Core Automotive |
| 49-3023 Auto Techs | 8,100 | 9,700 | 8,901 | 650 | Sales & Service |

---

### Attribution-Specific Files
**Files**:
- `data/processed/mi_occupation_employment_forecasts_bea_2024_2034.csv`
- `data/processed/mi_occupation_employment_forecasts_lightcast_2024_2034.csv`

**Use for**: Deep-dive analysis on attribution methodology sensitivity

---

## Key Metrics to Extract

### For Workforce Planning

1. **Top 10 Occupations by 2030 Employment**
   - Filter 2030 snapshot, group by occupation, take mean across methodologies
   - Use for training program prioritization

2. **Fastest Growing Occupations (2024-2030)**
   - Calculate % change from 2024 to 2030
   - Identify emerging skill needs

3. **Largest Absolute Gains/Losses**
   - Sort by absolute employment change
   - Focus on occupations with largest workforce implications

4. **Methodology Spread**
   - Compare min/max 2030 employment for each occupation
   - Large spreads indicate high uncertainty → additional research needed

### For Segment Analysis

1. **Total 2030 Employment by Segment**
   - Aggregate occupation-level to segment level
   - Compare to segment forecasts for validation

2. **Top 5 Occupations per Segment**
   - Within each segment, rank occupations by employment
   - Identifies segment-defining occupations

3. **Occupational Diversity**
   - Count unique occupations per segment
   - Calculate Herfindahl index (concentration)

---

## Troubleshooting

### Script Fails at Step 3
**Error**: `KeyError: 'segment_id'` or similar

**Solution**: The MCDA segment format changed. Check that line 168 of the script correctly extracts segment ID:
```python
mcda_2024['segment_id'] = mcda_2024['segment'].str.split('.').str[0].str.strip().astype(int)
```

---

### Missing BLS Shift Data
**Symptom**: Large number of occupations with `has_bls_shift=False`

**Explanation**: BLS doesn't publish industry×occupation matrices for all NAICS codes. Script falls back to constant share assumption.

**Impact**: Those occupations won't show within-segment occupational shifts. Segment growth still applied.

---

### Methodology Spread Too Large
**Symptom**: Min/max 2030 employment differ by >30% for many occupations

**Causes**:
1. **Attribution sensitivity**: BEA and Lightcast auto shares differ substantially for some industries
2. **Growth rate divergence**: Moody's and BLS project different industry trends

**Actions**:
1. Review attribution files for problematic NAICS codes
2. Compare Moody's vs. BLS growth assumptions
3. Consider validating with third source or stakeholder expertise

---

### Negative Employment Values
**Error**: Some occupation forecasts show negative employment

**Cause**: Occupational shift adjustment (BLS share changes) combined with segment decline

**Solution**: Post-process to set minimum floor (e.g., 0 or 1)

---

## Next Steps After Running Forecasts

1. **Validate 2030 projections**
   - Share top 20 occupations with industry experts
   - Compare to known capacity expansion/contraction plans

2. **Identify workforce development priorities**
   - Focus on high-growth occupations (>10% increase 2024-2030)
   - Cross-reference with regional training program capacity

3. **Document methodology uncertainty**
   - Flag occupations with >20% methodology spread
   - Conduct sensitivity analysis or scenario planning

4. **Integrate with labor market data**
   - Compare to job posting trends (Lightcast, Burning Glass)
   - Examine wage premiums for critical occupations
   - Assess educational pipeline (college programs, apprenticeships)

5. **Update periodically**
   - Re-run with updated QCEW data (annual)
   - Refresh with new BLS projections (biennial)
   - Adjust for major economic events (plant closures, policy changes)

---

## Questions or Issues?

**Data questions**: See [docs/data_sources.md](docs/data_sources.md) for source documentation

**Methodology questions**: See [docs/occupation_forecast_methodology.md](docs/occupation_forecast_methodology.md) for detailed technical explanation

**Script issues**: Check [scripts/README.md](scripts/README.md) for common problems and solutions

**Analysis examples**: Review [notebooks/14_occupation_forecasts.ipynb](notebooks/14_occupation_forecasts.ipynb) for worked examples

---

**Last Updated**: October 2025
**Analysis Period**: 2024-2034
**Priority Year**: 2030
