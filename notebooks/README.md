# Notebooks

This directory contains **Jupyter notebooks** for exploratory data analysis, visualization, and presentation of EV-Transition research findings. Notebooks combine code, narrative text, and visual outputs to document analytical workflows in a reproducible format.

## Notebook Organization

Notebooks are prefixed with ordinal numbers to indicate suggested execution order. This numbering reflects analytical dependencies—later notebooks often rely on datasets created by earlier ones.

## Notebook Inventory

### [03_growth_trajectories.ipynb](03_growth_trajectories.ipynb)
**Status**: Executed version available ([03_growth_trajectories_executed.ipynb](03_growth_trajectories_executed.ipynb))

**Purpose**: Analyzes employment growth trajectories across automotive segments using BLS and Moody's projections.

**Key Outputs**:
- Growth rate comparisons (historical vs. projected)
- Segment-specific trajectory charts
- Identification of high-growth and declining segments

**Data Sources**:
- BLS Employment Projections (Table 1.2)
- Moody's Analytics forecasts
- Segment assignments from `data/lookups/`

**Dependencies**: Requires processed BLS and Moody's data from earlier scripts.

---

### [04_mcda_staffing_analysis.ipynb](04_mcda_staffing_analysis.ipynb)
**Status**: Executed version available ([04_mcda_staffing_analysis_executed.ipynb](04_mcda_staffing_analysis_executed.ipynb))

**Purpose**: Examines Michigan Center for Data and Analytics (MCDA) staffing patterns across 10 automotive segments.

**Key Outputs**:
- Occupational composition by segment (2015, 2018, 2021, 2024)
- Temporal changes in staffing mix
- Michigan vs. US staffing pattern comparisons
- Critical occupation identification

**Data Sources**:
- `data/raw/Staffing Patterns for 10 Categories.xlsx`
- `data/interim/mcda_staffing_*.csv`
- US staffing patterns from BLS

**Related Scripts**:
- `scripts/process_mcda_staffing.py`
- `scripts/compare_us_mi_segments.py`

---

### [05_mi_qcew_time_series.ipynb](05_mi_qcew_time_series.ipynb)
**Purpose**: Initial exploration of Michigan QCEW employment time series (2001-2024).

**Key Outputs**:
- NAICS-level employment trends
- Identification of data quality issues (suppressions, breaks)
- Historical employment patterns by segment

**Data Sources**:
- `data/raw/MI-QCEW-38-NAICS-2001-2024.xlsx`
- `data/lookups/segment_assignments.csv`

**Related Scripts**: `scripts/process_mi_qcew_segments.py`

**Note**: This is an early exploratory notebook. Notebook 06 extends this analysis.

---

### [06_mi_qcew_time_series.ipynb](06_mi_qcew_time_series.ipynb)
**Purpose**: Refined QCEW time series analysis with segment aggregations.

**Key Outputs**:
- Segment-level employment time series (2001-2024)
- Stage-level rollups (Upstream/OEM/Downstream)
- Year-over-year growth calculations
- Employment weighting validation

**Data Sources**:
- `data/interim/mi_qcew_segment_employment_timeseries*.csv`
- `data/interim/mi_qcew_stage_employment_timeseries*.csv`

**Improvements over 05**: Better handling of NAICS code changes, weighted aggregations, stage hierarchies.

---

### [07_mi_us_moody_time_series.ipynb](07_mi_us_moody_time_series.ipynb)
**Status**: Executed version available ([08_mi_us_moody_time_series_executed.ipynb](08_mi_us_moody_time_series_executed.ipynb))

**Purpose**: Visualizes Moody's Analytics long-range forecasts (1970-2055) for Michigan and US automotive segments.

**Key Outputs**:
- **8 publication-ready figures** in `reports/figures/`:
  - MI segments: employment (1970-2055, 1990-2030)
  - MI segments: GDP (1970-2055, 1990-2030)
  - MI stages: employment and GDP (same time windows)
  - US segments: employment and GDP (same time windows)
  - US stages: employment and GDP (same time windows)

**Data Sources**:
- `data/interim/moodys_michigan_segments_timeseries*.csv`
- `data/interim/moodys_us_segments_timeseries*.csv`

**Related Scripts**: `scripts/process_moodys_time_series.py`

**Use Case**: Provides historical context and long-range perspective beyond QCEW 2001-2024 window.

---

### [09_qcew_mi_forecast_plots.ipynb](09_qcew_mi_forecast_plots.ipynb)
**Purpose**: Generates forecast visualizations combining QCEW historical data (2001-2024) with projections (2024-2034).

**Key Outputs**:
- Segment-level historical + forecast charts
- Stage-level aggregated forecasts
- Visual identification of trend breaks and projection uncertainty

**Data Sources**:
- `data/processed/mi_qcew_segment_employment_timeseries*.csv`
- `data/processed/mi_qcew_stage_employment_timeseries*.csv`

**Chart Style**: Line plots with distinct styling for historical (solid) vs. projected (dashed) periods.

---

### [10_mi_qcew_compare_forecasts.ipynb](10_mi_qcew_compare_forecasts.ipynb)
**Purpose**: **Baseline forecast methodology** comparison using direct Moody's + BLS growth application.

**Key Outputs**:
- **19 comparison charts** in `reports/figures/`:
  - 10 segment-level comparisons (Moody's vs. BLS extensions)
  - 3 stage-level comparisons
  - 6 additional diagnostic charts

**Methodology**: Applies Moody's sector forecasts and BLS industry projections directly to QCEW base without attribution adjustments.

**Data Sources**:
- `data/processed/mi_qcew_segment_employment_timeseries_extended*.csv`

**Related Scripts**: `scripts/apply_moodys_and_bls_growth_to_qcew.py`

---

### [11_mi_qcew_coreauto_compare_forecasts.ipynb](11_mi_qcew_coreauto_compare_forecasts.ipynb)
**Purpose**: **Lightcast/Core Auto methodology** forecast comparisons.

**Key Outputs**:
- **19 comparison charts** in `reports/figures/`:
  - 10 segment-level comparisons using Lightcast auto attribution
  - 3 stage-level comparisons
  - Moody's auto-specific vs. BLS non-auto growth splits

**Methodology**:
- Applies Lightcast-derived auto attribution shares to split each NAICS code
- Uses Moody's growth for auto-specific employment
- Uses BLS growth for non-auto employment within same NAICS

**Data Sources**:
- `data/raw/auto_attribution_core_auto_lightcast.csv`
- `data/processed/mi_qcew_segment_employment_timeseries_coreauto_extended*.csv`

**Related Scripts**: `scripts/apply_lightcast_share_and_extend.py`

**Comparison Focus**: Tests sensitivity to "core auto" vs. total industry definitions.

---

### [12_mi_qcew_bea_compare_forecasts.ipynb](12_mi_qcew_bea_compare_forecasts.ipynb)
**Purpose**: **BEA Attribution methodology** forecast comparisons.

**Key Outputs**:
- **19 comparison charts** in `reports/figures/`:
  - 10 segment-level comparisons using BEA auto attribution
  - 3 stage-level comparisons
  - Comparison to Lightcast and baseline approaches

**Methodology**:
- Applies Bureau of Economic Analysis auto attribution shares
- Same projection logic as Lightcast approach but with different attribution base
- Enables comparison of government vs. commercial attribution definitions

**Data Sources**:
- `data/raw/auto_attribution_bea.csv`
- `data/processed/mi_qcew_segment_employment_timeseries_bea_extended*.csv`

**Related Scripts**: `scripts/apply_bea_share_and_extend.py`

**Key Question**: How sensitive are projections to BEA vs. Lightcast auto-industry boundaries?

---

### [13_mi_qcew_compare_lightcast_vs_bea.ipynb](13_mi_qcew_compare_lightcast_vs_bea.ipynb)
**Purpose**: **Direct comparison of Lightcast vs. BEA attribution approaches**.

**Key Outputs**:
- **13 comparison charts** in `reports/figures/`:
  - 10 segments: Lightcast vs. BEA side-by-side (2001-2034)
  - 3 stages: Lightcast vs. BEA side-by-side (2001-2034)

**Analysis Focus**:
- Quantifies divergence between methodologies
- Identifies which segments are most attribution-sensitive
- Documents cases where methodology choice materially affects conclusions

**Data Sources**:
- `data/processed/mi_qcew_segment_employment_timeseries_lightcast_vs_bea_compare.csv`
- `data/processed/mi_qcew_stage_employment_timeseries_lightcast_vs_bea_compare.csv`

**Related Scripts**: `scripts/build_lightcast_vs_bea_comparison.py`

**Stakeholder Value**: Provides transparency on methodological uncertainty and supports informed methodology selection.

---

### [14_occupation_forecasts.ipynb](14_occupation_forecasts.ipynb)
**Purpose**: **Occupation-level employment forecasts (2024-2034)** with emphasis on 2030 projections for workforce planning.

**Key Outputs**:
- Occupation-level employment forecasts by segment, year, and methodology
- 2030 employment snapshot for all occupations across all segments
- Top occupations by employment and growth rate
- Fastest growing and declining occupations (2024-2030)
- Methodology comparison (BEA/Lightcast × Moody/BLS)
- Time series visualizations for top occupations

**Methodology**:
1. **Adjust 2024 MCDA staffing by auto attribution**:
   - Apply BEA and Lightcast auto shares to discount non-auto employment
   - Maintain proportional occupational mix within auto-specific employment

2. **Apply segment employment growth rates**:
   - Use segment forecasts from notebooks 10-12 (Moody's and BLS-derived)
   - Preserve separate growth scenarios for sensitivity analysis

3. **Account for occupational shifts**:
   - Incorporate BLS 2024-2034 occupational share changes
   - Linear interpolation of shares for intermediate years (2025-2033)
   - Fallback to constant share when BLS data unavailable

**Data Sources**:
- `data/interim/mcda_staffing_long_2021_2024.csv` - Base 2024 staffing patterns
- `data/raw/auto_attribution_bea.csv` - BEA auto attribution shares
- `data/raw/auto_attribution_core_auto_lightcast.csv` - Lightcast auto shares
- `data/processed/mi_qcew_segment_employment_timeseries_*_extended_*.csv` - Segment forecasts
- `data/raw/us_staffing_patterns/*.csv` - BLS occupational shift data

**Related Scripts**: `scripts/create_occupation_forecasts.py`

**Key Findings**:
- 4 methodology combinations produce 2030 employment range (sensitivity analysis)
- Identifies critical occupations for Michigan automotive workforce planning
- Documents occupational shifts within segments (e.g., increasing engineering roles, declining production roles)
- Highlights attribution sensitivity (BEA vs. Lightcast definitions)

**Outputs Saved**:
- `data/processed/mi_occupation_employment_forecasts_2024_2034.csv` - Full time series
- `data/processed/mi_occupation_employment_forecast_2030.csv` - 2030 snapshot
- `data/processed/mi_occupation_2030_summary_report.csv` - Stakeholder summary
- `reports/figures/occupation_*.png` - Multiple visualization charts

---

## Recommended Execution Order

### Initial Data Exploration
1. **03_growth_trajectories** - Understand overall growth patterns
2. **04_mcda_staffing_analysis** - Examine occupational composition
3. **05_mi_qcew_time_series** - Explore QCEW historical data
4. **06_mi_qcew_time_series** - Refined QCEW analysis with aggregations

### Forecasting Context
5. **07_mi_us_moody_time_series** - Long-range Moody's perspective (1970-2055)
6. **09_qcew_mi_forecast_plots** - Visualize historical + forecast integration

### Methodology Comparisons
7. **10_mi_qcew_compare_forecasts** - Baseline methodology
8. **11_mi_qcew_coreauto_compare_forecasts** - Lightcast attribution approach
9. **12_mi_qcew_bea_compare_forecasts** - BEA attribution approach
10. **13_mi_qcew_compare_lightcast_vs_bea** - Direct methodology comparison

### Occupation-Level Forecasts
11. **14_occupation_forecasts** - Occupation-level employment projections (2024-2034) with 2030 emphasis

## Output Summary

### Charts Generated (78 total)
- **Moody's long-range** (from notebook 07): 8 figures
- **Baseline forecasts** (from notebook 10): 19 figures
- **Lightcast forecasts** (from notebook 11): 19 figures
- **BEA forecasts** (from notebook 12): 19 figures
- **Lightcast vs. BEA** (from notebook 13): 13 figures

All figures saved to `reports/figures/` with descriptive filenames.

### Datasets Referenced
- **Raw**: `data/raw/*.xlsx` and `data/raw/*.csv`
- **Interim**: `data/interim/*_timeseries*.csv`
- **Processed**: `data/processed/*_extended*.csv`, `data/processed/*_compare.csv`

## Notebook Best Practices

### Structure Recommendations
Each notebook should include:

1. **Title & Context**: Brief description of analytical purpose
2. **Import Block**: Load libraries and set display options
3. **Data Loading**: Read required datasets with file paths documented
4. **Exploratory Analysis**: Iterative investigation with markdown narrative
5. **Key Findings**: Summarize insights in markdown cells
6. **Exports**: Save figures/tables to `reports/` with clear naming
7. **Next Steps**: Note follow-up questions or analyses needed

### Code Hygiene
- Clear variable names that reflect segment/stage/year context
- Markdown cells explaining "why" (code comments explain "how")
- Consistent plotting style (colors, fonts, figure sizes)
- Avoid hard-coded paths—use relative paths from notebook location

### Version Control
- Commit notebooks with outputs cleared (or keep executed versions separate)
- Name executed versions with `_executed` suffix
- Document major changes in git commit messages

## Exporting Figures

Standard export pattern used across notebooks:

```python
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(12, 6))
# ... plotting code ...
fig.savefig('../reports/figures/descriptive_filename.png', dpi=300, bbox_inches='tight')
plt.close()
```

**Naming Convention**: `mi_qcew_{segment/stage}_{name}_{methodology}_{start_year}_{end_year}.png`

Examples:
- `mi_qcew_segment_1_compare_2001_2034.png`
- `mi_qcew_bea_stage_upstream_compare_2001_2034.png`
- `moodys_us_segment_employment_1970_2055.png`

## Data Dependencies

### Scripts That Must Run Before Notebooks

**Core Processing**:
- `scripts/process_mi_qcew_segments.py` → Notebooks 05, 06
- `scripts/process_moodys_time_series.py` → Notebook 07

**Forecast Methodologies**:
- `scripts/apply_moodys_and_bls_growth_to_qcew.py` → Notebook 10
- `scripts/apply_lightcast_share_and_extend.py` → Notebook 11
- `scripts/apply_bea_share_and_extend.py` → Notebook 12

**Comparisons**:
- `scripts/build_lightcast_vs_bea_comparison.py` → Notebook 13

### Lookup Tables Required
- `data/lookups/segment_assignments.csv` - All notebooks
- `data/raw/auto_attribution_*.csv` - Notebooks 11, 12, 13

## Troubleshooting

### Missing Data Errors
If notebooks fail with "file not found":
1. Check that required scripts have been run (see Data Dependencies above)
2. Verify file paths are relative to notebook location (`../data/...`)
3. Ensure `data/lookups/segment_assignments.csv` is populated

### Plotting Errors
If charts don't render:
1. Verify matplotlib backend: `%matplotlib inline` at notebook start
2. Check for missing columns in dataframes (use `.columns` to inspect)
3. Validate year ranges in data match chart expectations

### Kernel Crashes
If kernel dies during execution:
1. Reduce data loading (filter to specific years or segments)
2. Clear outputs and restart kernel
3. Check memory usage with large Moody's time series (1970-2055)

## Related Documentation

- [../scripts/README.md](../scripts/README.md) - Scripts that generate notebook inputs
- [../data/README.md](../data/README.md) - Data pipeline and file structure
- [../reports/figures/](../reports/figures/) - Output directory for charts
- [../docs/methodology.md](../docs/methodology.md) - Analytical approach context

## Contributing New Notebooks

When creating a new notebook:

1. **Numbering**: Use next available number (14, 15, etc.)
2. **Descriptive Name**: `##_brief_topic_description.ipynb`
3. **Header Cell**: Add markdown cell with purpose, data sources, outputs
4. **Document Dependencies**: Note which scripts must run first
5. **Export Outputs**: Save figures to `reports/figures/` with clear names
6. **Update This README**: Add entry describing the new notebook

**Template Structure**:
```markdown
# Notebook Title

**Purpose**: [One sentence description]

**Data Sources**:
- [List input files]

**Key Outputs**:
- [List figures, tables, or processed datasets created]

**Dependencies**: [Required scripts or prior notebooks]
```

## Questions or Issues?

If you encounter problems with notebooks:
1. Check executed versions (`*_executed.ipynb`) to see expected outputs
2. Review script documentation in `scripts/README.md`
3. Verify data files exist in expected locations
4. Consult [docs/methodology.md](../docs/methodology.md) for analytical context
