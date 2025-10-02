# Methodology Notes

Use this log to record methodological decisions as the project evolves. Keeping a running narrative helps with reproducibility and stakeholder communication.

## Key Questions

- How do occupational staffing patterns differ across the ten supply-chain segments?
- Which industries anchor each segment, and what are their occupational mixes?
- How do Michigan staffing patterns compare to national benchmarks?

## Planned Approach

1. Identify the industries and NAICS codes assigned to each segment.
2. Pull staffing pattern data (e.g., OEWS) for the relevant industries.
3. Aggregate or weight occupational employment by segment, adjusting for Michigan-specific employment counts.
4. Highlight occupations that are over- or under-represented relative to statewide or national baselines.

## Open Decisions

- Weighting scheme for combining multi-industry or multi-region data.
- Treatment of suppressed or missing employment values.
- Granularity of occupations (SOC level) to use in reporting.

Add dated updates below as decisions are finalized:

### 2025-09-30

- Decision: Incorporate BLS 2024-2034 industry×occupation matrices as the national benchmark and compare segment shares against Michigan OEWS-derived staffing patterns.
- Rationale: Enables direct benchmarking of MCDA segment staffing against US norms without waiting for CSV exports behind BLS access controls.
- Impact: scripts/fetch_us_staffing.py, scripts/process_us_staffing_segments.py, and scripts/compare_us_mi_segments.py now produce side-by-side share comparisons and flag cases where broader NAICS fallbacks are used (e.g., 484000 for Truck Transportation).

### 2025-10-02

- Decision: Implement occupation-level employment forecasts (2024-2034) combining segment employment projections with occupational staffing pattern adjustments.
- Rationale: Workforce planning requires occupation-specific forecasts, not just segment totals. Three-step methodology balances data availability with analytical rigor:
  1. **Auto attribution adjustment**: Discount 2024 MCDA staffing patterns by BEA and Lightcast auto shares to isolate automotive-specific employment. Maintains proportional occupational mix within auto employment.
  2. **Segment growth application**: Apply segment-level forecasts (from Moody's and BLS) to scale occupational employment through 2034. Preserves 4 methodology combinations for sensitivity analysis.
  3. **Occupational shift incorporation**: Use BLS 2024-2034 industry×occupation projections to adjust within-segment occupational shares over time. Linear interpolation for intermediate years. Falls back to constant share when BLS data unavailable.
- Alternative approaches considered:
  - Direct application of US occupational growth rates: Rejected because Michigan automotive mix differs materially from US averages.
  - Constant occupational shares: Too simplistic; ignores known trends like automation, electrification skill shifts, and engineering workforce growth.
  - Segment-specific occupational shift models: Data requirements prohibit - would need historical MI staffing time series for each segment.
- Impact: New script (scripts/create_occupation_forecasts.py) and notebook (14_occupation_forecasts.ipynb) generate occupation-level projections. Key outputs:
  - `data/processed/mi_occupation_employment_forecasts_2024_2034.csv`: Full time series for all occupation-segment-methodology combinations
  - `data/processed/mi_occupation_employment_forecast_2030.csv`: 2030 snapshot (priority year for workforce planning)
  - `data/processed/mi_occupation_2030_summary_report.csv`: Stakeholder-ready summary with methodology ranges
- Limitations documented:
  - BLS occupational shift data not available for all NAICS codes in segment framework; uses constant share fallback
  - Attribution adjustment assumes occupational mix is similar between auto and non-auto portions of each industry (may not hold for all NAICS)
  - Does not model occupation-specific migration, retirement, or educational pipeline effects
- Next steps: Validate 2030 projections against stakeholder expectations; identify occupations requiring targeted workforce development interventions.
