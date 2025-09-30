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

- Decision: Incorporate BLS 2024–2034 industry–occupation matrices as the national benchmark and compare segment shares against Michigan OEWS-derived staffing patterns.
- Rationale: Enables direct benchmarking of MCDA segment staffing against US norms without waiting for CSV exports behind BLS access controls.
- Impact: scripts/fetch_us_staffing.py, scripts/process_us_staffing_segments.py, and scripts/compare_us_mi_segments.py now produce side-by-side share comparisons and flag cases where broader NAICS fallbacks are used (e.g., 484000 for Truck Transportation).
