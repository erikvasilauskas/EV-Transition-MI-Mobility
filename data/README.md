# Data Directory

This folder stores datasets and intermediate outputs for the EV-Transition staffing analysis project.

- aw/: Unmodified source files pulled from public data providers or partners. Key additions include:
  - Occupation_2023_ep.xlsx / occupation_2024_ep.xlsx (BLS projections tables)
  - Staffing Patterns for 10 Categories.xlsx (MCDA aggregations)
  - us_staffing_patterns/ (BLS industry–occupation matrices retrieved via scripts/fetch_us_staffing.py).
- external/: Reference datasets used for joins (e.g., NAICS crosswalks, occupational taxonomies).
- interim/: Cleaned or lightly transformed tables ready for feature engineering. Notable examples are
  - occupation_table12_tidy.csv (BLS Table 1.2 comparisons)
  - mcda_staffing_wide_2021_2024.csv / mcda_staffing_long_2021_2024.csv
  - us_staffing_segments_long_2024_2034.csv.
- processed/: Analysis-ready tables and comparison summaries such as mcda_staffing_*, occupation_table12_comparison.*, and the US vs. Michigan share comparisons.
- lookups/: Controlled vocabularies and mapping tables, such as NAICS-to-segment assignments enriched with 2024 QCEW employment and projection deltas.

Keep personally identifying information (PII) or restricted-use data out of this repository. Use .gitignore rules if you need to stage sensitive files locally.
