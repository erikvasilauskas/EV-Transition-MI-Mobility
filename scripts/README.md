# Scripts Directory

This directory contains **executable Python scripts** for data processing, forecasting, and analysis. Scripts are designed to be run from the command line and produce datasets in the `data/` directory.

## Script Categories

### Data Processing Scripts

#### [process_mi_qcew_segments.py](process_mi_qcew_segments.py)
**Purpose**: Transforms raw Michigan QCEW data into segment-level time series (2001-2024).

**Inputs**:
- `data/raw/MI-QCEW-38-NAICS-2001-2024.xlsx`
- `data/lookups/segment_assignments.csv`

**Outputs**:
- `data/interim/mi_qcew_segment_employment_timeseries.csv`
- `data/interim/mi_qcew_stage_employment_timeseries.csv`

**Run frequency**: After QCEW data updates (annual)

---

#### [process_moodys_time_series.py](process_moodys_time_series.py)
**Purpose**: Standardizes Moody's long-range forecasts (1970-2055) for Michigan and US.

**Inputs**:
- `data/raw/Moody's Supply Chain Employment and Output 1970-2055.xlsx`
- `data/lookups/segment_assignments.csv`

**Outputs**:
- `data/interim/moodys_michigan_segments_timeseries.csv`
- `data/interim/moodys_michigan_stages_timeseries.csv`
- `data/interim/moodys_us_segments_timeseries.csv`
- `data/interim/moodys_us_stages_timeseries.csv`
- YoY growth rate versions (`*_yoy.csv`)

**Run frequency**: After Moody's data updates (quarterly)

---

#### [process_mcda_staffing.py](process_mcda_staffing.py)
**Purpose**: Cleans and normalizes MCDA occupational staffing patterns for 10 segments.

**Inputs**:
- `data/raw/Staffing Patterns for 10 Categories.xlsx`

**Outputs**:
- `data/interim/mcda_staffing_wide_2021_2024.csv`
- `data/interim/mcda_staffing_long_2021_2024.csv`

**Run frequency**: When MCDA updates staffing data

---

### Forecast Methodology Scripts

#### [apply_moodys_and_bls_growth_to_qcew.py](apply_moodys_and_bls_growth_to_qcew.py)
**Purpose**: **Baseline forecast** - Direct application of Moody's and BLS growth to QCEW.

**Methodology**: No attribution adjustment; uses sector-level Moody's forecasts and BLS industry projections.

**Outputs**:
- `data/processed/mi_qcew_segment_employment_timeseries_extended.csv`
- `data/processed/mi_qcew_segment_employment_timeseries_extended_moody.csv`
- `data/processed/mi_qcew_segment_employment_timeseries_extended_bls.csv`
- Stage-level versions

**Dependencies**: Requires `process_mi_qcew_segments.py` and `process_moodys_time_series.py`

---

#### [apply_lightcast_share_and_extend.py](apply_lightcast_share_and_extend.py)
**Purpose**: **Lightcast/Core Auto forecast** - Applies Lightcast auto attribution shares.

**Methodology**:
1. Split NAICS employment into auto-specific and non-auto portions using Lightcast shares
2. Apply Moody's growth to auto-specific, BLS growth to non-auto
3. Aggregate to segments

**Outputs**:
- `data/processed/mi_qcew_segment_employment_timeseries_coreauto_extended_moody.csv`
- `data/processed/mi_qcew_segment_employment_timeseries_coreauto_extended_bls.csv`
- Diagnostic and comparison files

**Dependencies**: Requires `data/raw/auto_attribution_core_auto_lightcast.csv`

---

#### [apply_bea_share_and_extend.py](apply_bea_share_and_extend.py)
**Purpose**: **BEA Attribution forecast** - Applies Bureau of Economic Analysis auto shares.

**Methodology**: Same as Lightcast approach but with BEA auto attribution definitions.

**Outputs**:
- `data/processed/mi_qcew_segment_employment_timeseries_bea_extended_moody.csv`
- `data/processed/mi_qcew_segment_employment_timeseries_bea_extended_bls.csv`
- Diagnostic and comparison files

**Dependencies**: Requires `data/raw/auto_attribution_bea.csv`

---

#### [create_occupation_forecasts.py](create_occupation_forecasts.py) ⭐ **NEW**
**Purpose**: **Occupation-level forecasts (2024-2034)** with emphasis on 2030.

**Methodology**:
1. Adjust 2024 MCDA staffing by auto attribution (BEA and Lightcast)
2. Apply segment growth rates (Moody's and BLS)
3. Incorporate BLS occupational shift trends (2024-2034)

**Outputs**:
- `data/processed/mi_occupation_employment_forecasts_2024_2034.csv` - Full time series
- `data/processed/mi_occupation_employment_forecast_2030.csv` - 2030 snapshot
- `data/processed/mi_occupation_2030_summary_report.csv` - Stakeholder summary
- Separate BEA and Lightcast files

**Dependencies**: Requires all segment forecasts and BLS staffing patterns

**Run time**: ~2-5 minutes

**Documentation**: See [../docs/occupation_forecast_methodology.md](../docs/occupation_forecast_methodology.md)

---

### Growth Rate & Comparison Scripts

#### [compute_bls_growth_timeseries.py](compute_bls_growth_timeseries.py)
**Purpose**: Calculates year-over-year growth rates from BLS Employment Projections.

**Outputs**:
- `data/interim/bls_us_segments_timeseries_yoy.csv`
- `data/interim/bls_us_stages_timeseries_yoy.csv`

---

#### [build_lightcast_vs_bea_comparison.py](build_lightcast_vs_bea_comparison.py)
**Purpose**: Direct comparison of Lightcast and BEA attribution methodologies.

**Outputs**:
- `data/processed/mi_qcew_segment_employment_timeseries_lightcast_vs_bea_compare.csv`
- `data/processed/mi_qcew_stage_employment_timeseries_lightcast_vs_bea_compare.csv`

---

#### [compare_us_mi_segments.py](compare_us_mi_segments.py)
**Purpose**: Compares Michigan vs. US staffing pattern shares for benchmarking.

**Outputs**: Various `us_mi_segment_comparison_*.csv` files

---

### US Data Retrieval Scripts

#### [fetch_us_staffing.py](fetch_us_staffing.py)
**Purpose**: Automated retrieval of BLS industry×occupation matrices (Table 1.9).

**Outputs**: Creates `data/raw/us_staffing_patterns/*.csv` (one file per NAICS code)

**Run frequency**: Biennial (when new BLS projections released)

**Note**: Web scraping script; may need updates if BLS website structure changes

---

### Utility & Notebook Generation Scripts

#### [create_growth_notebook.py](create_growth_notebook.py)
**Purpose**: Programmatically generates growth trajectory notebook.

---

#### [create_mcda_staffing_notebook.py](create_mcda_staffing_notebook.py)
**Purpose**: Programmatically generates MCDA staffing analysis notebook.

---

#### [aggregate_moodys_segments.py](aggregate_moodys_segments.py)
**Purpose**: Aggregates Moody's data by segment and stage.

---

### Diagnostic & Debug Scripts

#### [test_occupation_forecast_data.py](test_occupation_forecast_data.py) ⭐ **NEW**
**Purpose**: Validates data availability before running occupation forecasts.

**Run this first**: Before executing `create_occupation_forecasts.py`

**Checks**:
- MCDA 2024 data presence
- Segment assignment completeness
- Attribution file coverage
- Segment forecast availability
- BLS staffing pattern files
- Data alignment (segments match across sources)

**Run time**: <10 seconds

---

### Legacy/Debug Scripts

- `check_4571_mi.py` - Debug script for specific NAICS code
- `debug_mi_4571.py` - NAICS 4571 validation
- `debug_mi_table.py` - Table structure debugging
- `debug_moodys_mi.py` - Moody's Michigan data validation
- `explore_moody.py` - Interactive Moody's data exploration
- `inspect_moody.py` - Moody's file structure inspection
- `inspect_occupation_workbooks.py` - BLS occupation workbook inspection
- `moodys_metrics.py` - Moody's metric extraction
- `moodys_metric_geo.py` - Geographic Moody's metrics
- `moodys_mnemonics.py` - Moody's variable name decoder

---

## Recommended Execution Sequence

### Initial Setup (One-Time)
1. `fetch_us_staffing.py` - Retrieve BLS staffing patterns
2. `process_mcda_staffing.py` - Clean MCDA data

### Annual Data Refresh
When new QCEW data arrives:

1. Update `data/raw/MI-QCEW-38-NAICS-YYYY-YYYY.xlsx`
2. Run `process_mi_qcew_segments.py`
3. Run all three forecast scripts:
   - `apply_moodys_and_bls_growth_to_qcew.py`
   - `apply_lightcast_share_and_extend.py`
   - `apply_bea_share_and_extend.py`
4. Run `build_lightcast_vs_bea_comparison.py`
5. Run `test_occupation_forecast_data.py` (validation)
6. Run `create_occupation_forecasts.py`

### Quarterly Moody's Update (Optional)
1. Update `data/raw/Moody's Supply Chain Employment and Output YYYY-YYYY.xlsx`
2. Run `process_moodys_time_series.py`
3. Re-run forecast scripts (steps 3-6 above)

### Biennial BLS Update
When new BLS Employment Projections released:

1. Run `fetch_us_staffing.py` to get updated Table 1.9
2. Update `data/raw/occupation_YYYY_ep.xlsx`
3. Run `compute_bls_growth_timeseries.py`
4. Re-run forecast scripts
5. Re-run `create_occupation_forecasts.py` (to get new occupational shifts)

---

## Script Development Guidelines

### Structure
All scripts should follow this pattern:
```python
"""
Brief description of what the script does.

Inputs:
- List input files

Outputs:
- List output files
"""

import pandas as pd
from pathlib import Path

# Define paths
BASE_DIR = Path(__file__).parent.parent
DATA_RAW = BASE_DIR / "data" / "raw"
DATA_INTERIM = BASE_DIR / "data" / "interim"
DATA_PROCESSED = BASE_DIR / "data" / "processed"

# Main processing logic
if __name__ == "__main__":
    # Step 1: Load data
    # Step 2: Process
    # Step 3: Save outputs
    # Step 4: Print summary
```

### Error Handling
- Use `try/except` for file I/O operations
- Print informative error messages with file paths
- Validate input data before processing (check for required columns)

### Output Messages
- Print section headers (`[1/N] Loading data...`)
- Report record counts after each major step
- Summarize outputs at the end
- Use progress indicators for long-running operations

### Documentation
- Docstring at top with inputs/outputs
- Comments for complex logic
- Print statements to explain what's happening

---

## Common Issues & Solutions

### Python Not Found
**Problem**: `Python was not found` error on Windows

**Solution**:
- Use full path: `C:\Path\To\python.exe script_name.py`
- Or activate conda environment: `conda activate your_env`

### Missing Input Files
**Problem**: `FileNotFoundError` for input data

**Solution**:
- Check that prerequisite scripts have been run
- Verify file paths in script match actual data locations
- Ensure working directory is project root

### Memory Errors
**Problem**: Script crashes with memory error

**Solution**:
- Filter data to specific years/segments
- Process in chunks (use `chunksize` parameter in `pd.read_csv`)
- Close unused dataframes with `del df`

### NAICS Code Mismatches
**Problem**: Segment aggregations missing data

**Solution**:
- Check that `segment_assignments.csv` covers all needed NAICS codes
- Verify NAICS code formats (integers vs. strings with leading zeros)
- Look for attribution file coverage gaps

### Year Range Errors
**Problem**: Forecast years don't align

**Solution**:
- Ensure all forecast scripts use same year range (2024-2034)
- Check that base year (2024) exists in QCEW data
- Verify Moody's projections cover required years

---

## Testing Scripts

Before running production scripts:

1. **Test with small sample**: Comment out full data load, use `.head(100)`
2. **Validate outputs**: Check column names, data types, record counts
3. **Compare to prior runs**: Ensure results are stable
4. **Run diagnostic script**: Use `test_occupation_forecast_data.py` for occupation forecasts

---

## Performance Notes

Approximate run times on typical workstation:

| Script | Run Time | Bottleneck |
|--------|----------|------------|
| process_mi_qcew_segments.py | 30 sec | Excel read |
| process_moodys_time_series.py | 1 min | Multiple sheets |
| apply_*_share_and_extend.py | 1-2 min | Segment loops |
| create_occupation_forecasts.py | 2-5 min | Occupation×segment×year loops |
| build_lightcast_vs_bea_comparison.py | 30 sec | I/O |
| fetch_us_staffing.py | 5-10 min | Web requests |

---

## Migration to src/ Package (Future)

These scripts are candidates for refactoring into reusable modules:

**High priority**:
- Data loading functions (QCEW, Moody's, BLS patterns)
- Attribution logic (BEA, Lightcast share application)
- Growth rate calculations
- Segment aggregation utilities

**Medium priority**:
- Forecasting logic
- Comparison calculations
- Diagnostic functions

See [../src/README.md](../src/README.md) for migration plan.

---

## Additional Resources

- **Notebooks**: See [../notebooks/README.md](../notebooks/README.md) for analysis notebooks
- **Methodology**: See [../docs/methodology.md](../docs/methodology.md) for decision log
- **Data**: See [../data/README.md](../data/README.md) for file descriptions
- **Occupation Forecasts**: See [../docs/occupation_forecast_methodology.md](../docs/occupation_forecast_methodology.md)

---

**For questions about specific scripts**: Check docstrings and comments in the script source code, or review related notebooks for worked examples.
