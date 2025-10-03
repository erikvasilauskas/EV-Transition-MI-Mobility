# EV-Transition

Comprehensive analytical toolkit for understanding Michigan's automotive supply chain transition to electric vehicles through the lens of occupational staffing patterns, employment projections, and economic indicators.

## Project Overview

This repository supports economic development planning by analyzing how the shift to electric vehicles impacts **10 distinct automotive supply-chain segments** in Michigan. The analysis combines historical employment data (2001-2024), multiple forecast methodologies (2024-2034), and occupational staffing patterns to identify workforce risks and opportunities.

## Core Objectives

1. **Industry Segmentation**: Define and maintain consistent NAICS code mappings for 10 automotive supply-chain segments spanning upstream materials through downstream sales and service
2. **Employment Forecasting**: Project segment-level employment through 2034 using three methodologies (Lightcast/Core Auto, BEA attribution, baseline Moody's+BLS)
3. **Staffing Analysis**: Combine occupational staffing patterns (OEWS/MCDA) with Michigan employment counts to identify critical, emerging, or at-risk occupations
4. **Benchmarking**: Compare Michigan staffing patterns against US national baselines using BLS industry×occupation matrices
5. **Reproducible Outputs**: Generate publication-ready datasets, visualizations, and documentation for economic development partners

## Supply-Chain Architecture

The analysis framework divides the automotive ecosystem into **3 stages** and **10 segments**:

### Upstream (Segments 1-5)
- **Segment 1**: Materials & Processing (Metals, Non-Metals, Coatings & Surface Treatments)
- **Segment 2**: Equipment Manufacturing (Metalworking, General Purpose Machinery)
- **Segment 3**: Forging & Foundries
- **Segment 4**: Parts & Machining (Machine Shops, Fabricated Metal, Semiconductors)
- **Segment 5**: Component Systems (Engines, Power Transmission, Control Instruments)

### OEM (Segments 6-7)
- **Segment 6**: Engineering & Design (Architectural/Engineering Services, R&D)
- **Segment 7**: Core Automotive (Vehicle Manufacturing, Body/Trailer, Parts Manufacturing)

### Downstream (Segments 8-10)
- **Segment 8**: Motor Vehicle Parts, Materials, & Products Sales (Wholesale)
- **Segment 9**: Vehicle Sales & Service (Dealers, Repair/Maintenance)
- **Segment 10**: Logistics & Transportation (Warehousing, Truck Transportation)

**Total Coverage**: 38 NAICS codes representing ~550,000 Michigan jobs (2024 QCEW)

## Data Pipeline Workflow

### 1. Data Acquisition & Documentation
- Document segment definitions and methodological decisions in `docs/`
- Stage raw datasets from BLS (QCEW, OEWS, Employment Projections), Moody's Analytics, and MCDA in `data/raw/`
- Maintain authoritative NAICS-to-segment mappings in `data/lookups/segment_assignments.csv`

### 2. Data Transformation
- Run ETL scripts in `scripts/` to clean, normalize, and transform raw data
- Generate intermediate datasets in `data/interim/` (time series, growth rates, diagnostics)
- Apply three forecast methodologies to extend 2001-2024 historical data through 2034

### 3. Analysis & Aggregation
- Aggregate employment by segment and stage using QCEW weights
- Compute year-over-year growth rates and projection deltas
- Compare Michigan vs. US staffing pattern shares
- Export analysis-ready datasets to `data/processed/`

### 4. Visualization & Reporting
- Create exploratory notebooks in `notebooks/` for iterative analysis
- Generate publication-ready figures (line charts, comparison plots) in `reports/figures/`
- Document findings and methodological decisions in `docs/methodology.md`

## Key Data Sources

| Source | Provider | Purpose | Update Frequency |
|--------|----------|---------|------------------|
| **QCEW** | BLS via MI Dept of Labor | Michigan employment by NAICS (2001-2024) | Annual |
| **OEWS** | BLS via MCDA | Michigan occupational staffing patterns | Annual |
| **Moody's Analytics** | Moody's Economy.com | Long-range employment/GDP forecasts (1970-2055) | Quarterly |
| **BLS Employment Projections** | BLS Table 1.9 | US industry×occupation matrices (2024-2034) | Annual |
| **BEA/Lightcast Attribution** | Project analysis | Auto-industry share allocations | As needed |
| **MCDA Staffing Patterns** | MI Center for Data & Analytics | Aggregated 10-segment staffing patterns | On demand |

See [docs/data_sources.md](docs/data_sources.md) for detailed access information and licensing terms.

## Repository Structure

```
├── config/                   # Configuration templates
├── data/                     # Data pipeline (see data/README.md)
│   ├── raw/                  # Source files from external providers
│   ├── external/             # Reference datasets for joins
│   ├── lookups/              # NAICS-segment mappings and controlled vocabularies
│   ├── interim/              # Cleaned/transformed intermediate outputs
│   └── processed/            # Analysis-ready datasets and comparisons
├── docs/                     # Project documentation (see docs/README.md)
│   ├── segment_definitions.md
│   ├── data_sources.md
│   └── methodology.md
├── notebooks/                # Jupyter notebooks for exploration (see notebooks/README.md)
├── references/               # External research and supporting literature
├── reports/                  # Publication-ready outputs
│   └── figures/              # 78 PNG charts (segment/stage forecasts)
├── scripts/                  # ETL and analysis scripts (see scripts/README.md)
│   ├── process_*.py          # Data processing pipelines
│   ├── apply_*.py            # Forecast methodology implementations
│   ├── compute_*.py          # Growth rate calculations
│   └── compare_*.py          # Cross-methodology comparisons
└── src/                      # Reusable Python modules
    ├── data_processing/      # ETL utilities
    ├── analysis/             # Analytical functions
    └── visualization/        # Plotting helpers
```

## Recent Enhancements (Sept-Oct 2025)

### Forecasting Pipeline Expansion
Implemented three parallel forecast methodologies to test sensitivity of employment projections:

- **Lightcast/Core Auto Methodology** ([apply_lightcast_share_and_extend.py](scripts/apply_lightcast_share_and_extend.py))
  - Uses Lightcast-derived auto attribution shares
  - Applies Moody's growth rates to auto-specific employment
  - Extends BLS growth to non-auto employment within each NAICS

- **BEA Attribution Methodology** ([apply_bea_share_and_extend.py](scripts/apply_bea_share_and_extend.py))
  - Uses Bureau of Economic Analysis auto-sector shares
  - Same projection logic as Lightcast approach with different base shares

- **Baseline Moody's+BLS** ([apply_moodys_and_bls_growth_to_qcew.py](scripts/apply_moodys_and_bls_growth_to_qcew.py))
  - Direct application of Moody's sector-level forecasts
  - BLS Employment Projections for supplemental industries

### Data Processing Enhancements
- Automated QCEW time series processing ([process_mi_qcew_segments.py](scripts/process_mi_qcew_segments.py))
- Moody's data standardization for MI and US ([process_moodys_time_series.py](scripts/process_moodys_time_series.py))
- BLS year-over-year growth computation ([compute_bls_growth_timeseries.py](scripts/compute_bls_growth_timeseries.py))
- Cross-methodology comparison tool ([build_lightcast_vs_bea_comparison.py](scripts/build_lightcast_vs_bea_comparison.py))

### Visualization & Analysis
- **78 publication-ready figures** generated in `reports/figures/`:
  - 10 segments × 3 forecast methodologies = 30 segment charts
  - 3 stages × 3 forecast methodologies = 9 stage charts
  - 10 segments + 3 stages × Lightcast vs. BEA = 13 comparison charts
  - 8 Moody's long-range projection charts (MI/US × segments/stages)

- **13 executed Jupyter notebooks** documenting workflows:
  - Growth trajectories analysis
  - MCDA staffing patterns
  - QCEW time series processing
  - Moody's forecast visualization
  - Cross-methodology comparisons

### US Benchmarking Capability
- Automated US industry×occupation matrix retrieval ([fetch_us_staffing.py](scripts/fetch_us_staffing.py))
- Michigan vs. US segment staffing pattern comparisons ([compare_us_mi_segments.py](scripts/compare_us_mi_segments.py))
- Processing pipelines for MCDA and US staffing data
- Identification of NAICS fallback scenarios for missing granular data

## Getting Started

### Prerequisites
- Python 3.8+ with pandas, numpy, matplotlib, seaborn, openpyxl
- Jupyter Notebook/Lab for interactive analysis
- Git for version control

### Initial Setup
1. Clone the repository
2. Review segment definitions in [docs/segment_definitions.md](docs/segment_definitions.md)
3. Examine NAICS-to-segment mappings in [data/lookups/segment_assignments.csv](data/lookups/segment_assignments.csv)
4. Check data source documentation in [docs/data_sources.md](docs/data_sources.md)

### Running Analyses
1. **Process QCEW Time Series**: Run [scripts/process_mi_qcew_segments.py](scripts/process_mi_qcew_segments.py)
2. **Apply Forecast Methodology**: Choose from `apply_lightcast_share_and_extend.py`, `apply_bea_share_and_extend.py`, or `apply_moodys_and_bls_growth_to_qcew.py`
3. **Generate Comparisons**: Run [scripts/build_lightcast_vs_bea_comparison.py](scripts/build_lightcast_vs_bea_comparison.py)
4. **Visualize Results**: Execute notebooks in `notebooks/` (recommended order: 05 → 13)

### Key Output Files
- `data/processed/mi_qcew_segment_employment_timeseries*.csv` - Segment-level forecasts
- `data/processed/mi_qcew_stage_employment_timeseries*.csv` - Stage-level rollups
- `data/processed/*_compare.csv` - Cross-methodology comparisons
- `reports/figures/*.png` - Publication-ready charts

## Methodology Highlights

### Employment Weighting
Uses 2024 QCEW employment counts as weights to aggregate multi-industry segments. Each NAICS code's contribution is proportional to its Michigan employment.

### Forecast Horizons
- **Historical**: 2001-2024 (observed QCEW data)
- **Projection**: 2024-2034 (aligned with BLS 10-year projection cycle)
- **Long-range context**: 1970-2055 (Moody's Analytics for trend context)

### Attribution Approaches
- **Lightcast Core Auto**: Industry-specific research on auto manufacturing exposure
- **BEA**: Official government statistics on auto sector boundaries
- **Comparison rationale**: Tests sensitivity to different definitions of "automotive industry"

### Data Quality Considerations
- Handles NAICS code changes over time (2002, 2007, 2012, 2017 revisions)
- Addresses data suppression in small employment cells
- Documents NAICS fallback strategies when granular staffing data unavailable
- Validates Moody's sector mappings against QCEW actuals

See [docs/methodology.md](docs/methodology.md) for detailed methodological decisions and dated updates.

## Current Outputs

### Datasets (data/processed/)
- 30 segment-level time series files (10 segments × 3 methodologies)
- 9 stage-level time series files (3 stages × 3 methodologies)
- 13 comparison files (segments/stages × Lightcast vs. BEA)
- Diagnostic files showing forecast methodology differences

### Visualizations (reports/figures/)
- Historical + forecast line charts (2001-2034) for all segments
- Stage-level aggregations showing upstream/OEM/downstream trends
- Side-by-side methodology comparisons
- Moody's long-range projections (1970-2055) with full economic cycles

## Next Steps & Future Enhancements

### Immediate Priorities
- [ ] Finalize occupational granularity decision (2-digit vs. 6-digit SOC codes)
- [ ] Determine preferred forecast methodology based on stakeholder input
- [ ] Curate reporting-ready comparison datasets for economic development partners
- [ ] Document occupation-level findings (critical, emerging, at-risk roles)

### Expansion Opportunities
- [ ] Extend geographic benchmarking beyond US national (peer states, metro areas)
- [ ] Incorporate wage/earnings projections alongside employment
- [ ] Add scenario analysis (accelerated vs. delayed EV adoption)
- [ ] Integrate educational attainment data for workforce pipeline planning
- [ ] Develop occupation-to-training program crosswalks

### Technical Improvements
- [ ] Migrate scripts to modular `src/` package structure
- [ ] Add unit tests for key transformation functions
- [ ] Create command-line interface for running full pipeline
- [ ] Implement automated data validation checks
- [ ] Set up continuous integration for reproducibility testing

## Contributing

This is an internal economic development project. For questions or collaboration opportunities:

1. Review existing documentation in `docs/`
2. Examine methodology notes for context on analytical decisions
3. Check `notebooks/` for worked examples of data processing steps
4. Consult `scripts/` source code for implementation details

## License & Data Use

- **Analysis code**: Internal use for Michigan economic development planning
- **Data licensing**: Varies by source (see [docs/data_sources.md](docs/data_sources.md))
  - BLS data: Public domain
  - Moody's Analytics: Licensed data, not for redistribution
  - MCDA staffing patterns: Internal use only

Do not redistribute raw data files without verifying licensing terms. Processed analytical outputs may be shared with authorized economic development partners.

## Contact & Support

For questions about this analysis:
- Review documentation in `docs/` folder
- Examine executed notebooks in `notebooks/` for analytical context
- Check methodology notes for decision rationale

---

**Last Updated**: October 2025
**Analysis Period**: 2001-2034 (historical + projections)
**Geographic Focus**: Michigan, with US national benchmarking
