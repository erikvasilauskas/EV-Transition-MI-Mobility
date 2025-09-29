# EV-Transition

Toolkit for analyzing occupational staffing patterns across ten Michigan automotive supply-chain segments.

## Objectives
- Define a consistent set of industries and NAICS codes for each segment.
- Combine occupational staffing patterns with Michigan employment counts.
- Surface occupations that are critical, emerging, or at risk within each segment.
- Share clean, reproducible outputs with economic development partners.

## Workflow At A Glance
1. Document supply-chain segments and source data under `docs/`.
2. Stage raw datasets (e.g., OEWS, QCEW) in `data/raw/` and refresh lookup tables in `data/lookups/`.
3. Build cleaning and transformation scripts inside `src/data_processing/` to populate `data/interim/`.
4. Aggregate segment and occupational metrics via modules in `src/analysis/`, exporting results to `data/processed/`.
5. Craft notebooks in `notebooks/` for exploration, and publish visuals or tables in `reports/`.

## Repository Layout
```
config/                Configuration templates for project- and segment-level settings
data/                  Raw, intermediate, and processed datasets plus lookup tables
docs/                  Segment definitions, data source catalogue, and methodology notes
notebooks/             Exploratory and presentation-ready notebooks
references/            External research and supporting literature
reports/               Publication-ready figures and tables
src/                   Reusable ETL, analysis, and visualization code modules
```

## Getting Started
- Update `docs/segment_definitions.md` with the ten segments and representative industries.
- Populate `data/lookups/segment_assignments.csv` with definitive NAICS-to-segment mappings.
- Record source metadata and access details in `docs/data_sources.md`.
- Draft ETL scripts in `src/data_processing/` and commit any shared helpers.

## Next Steps
- Identify priority datasets (OEWS, QCEW, custom surveys) and document refresh cadence.
- Decide on occupational granularity (2-digit vs. 6-digit SOC) and weighting approach.
- Create an initial notebook (e.g., `01_segment_profiles.ipynb`) to validate the pipeline end-to-end.
