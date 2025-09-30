# Data Sources

Use this catalogue to track all data inputs used in the staffing pattern analysis. Capture refresh cadence, licensing, and transformation notes for each asset.

| Dataset | Provider | Access Method | Refresh Cadence | License/Terms | Notes |
|---------|----------|---------------|-----------------|--------------|-------|
| QCEW employment | BLS | Downloaded CSV (MiDems portal) | Annual | Public | Used for 2024 employment weights joined to segment lookup. |
| OEWS staffing patterns | BLS | Michigan OEWS extracts via MCDA | Annual | Public | Source of Michigan staffing patterns for 2015, 2018, 2021, 2024. |
| Industry segment mapping | Project-defined | data/lookups/segment_assignments.csv | As needed | Internal | Maintains NAICS-to-segment assignments and projection metadata. |
| BLS Table 1.2 Occupational projections | BLS Employment Projections | data/raw/occupation_2023_ep.xlsx, occupation_2024_ep.xlsx | Biennial | Public | Scripts normalize Annex Table 1.2 for 2023 & 2024 to compare projections. |
| MCDA staffing patterns (10 segments) | Michigan Center for Data and Analytics | data/raw/Staffing Patterns for 10 Categories.xlsx | Provided updates | Internal | Source for Michigan segment rollups processed via scripts/process_mcda_staffing.py. |
| US industry–occupation matrix (Table 1.9) | BLS Employment Projections | Automated HTML scrape (scripts/fetch_us_staffing.py) | Biennial | Public | Produces data/raw/us_staffing_patterns/*.csv for benchmarking US vs. Michigan segments. |

Document any bespoke datasets (e.g., regional surveys) with enough detail to reproduce the extraction process later.
