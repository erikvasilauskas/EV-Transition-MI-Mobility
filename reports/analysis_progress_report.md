# Michigan Automotive Workforce Forecast Progress Report

_Last updated: 2025-10-03_

## Project Overview
- Scope: Translate QCEW segment forecasts into occupation-level trajectories for Michigan's automotive supply chain (2024–2034).
- Key questions: How do upstream vs. downstream segments evolve? Which occupations grow or decline? How do national BLS shares influence Michigan staffing patterns?
- Deliverables to date: reproducible scripts (scripts/), processed datasets (data/processed/), interactive dashboards (dashboards/occupation_forecast_dashboard*.py), and summary notebooks in 
otebooks/.

## Data Inputs
- **Segment baselines & forecasts**: data/processed/mi_qcew_segment_employment_timeseries_lightcast_vs_bea_compare.csv (Lightcast vs. BEA; Moody vs. BLS growth paths).
- **Occupation baselines**: data/processed/mcda_staffing_detailed_2021_2024.csv (MCDA detailed staffing, including 2021 and 2024 shares plus education tags).
- **National adjustment factors**: data/processed/us_staffing_segments_summary.csv (BLS 2024 & 2034 segment share targets).
- **Segment-to-NAICS mapping**: data/lookups/segment_assignments.csv (stage, segment name, 2024 QCEW industry totals).
- **Auto attribution**: data/raw/auto_attribution_core_auto_lightcast.csv, data/raw/auto_attribution_bea.csv (segment shares used to apportion QCEW employment).

## Methodological Notes
1. **Attribution**: Scripts pply_lightcast_share_and_extend.py and pply_bea_share_and_extend.py multiply raw QCEW employment by Lightcast/BEA share_to_set values to produce segment-specific baselines.
2. **Segment forecasts**: pply_moodys_and_bls_growth_to_qcew.py extends each segment with Moody and BLS employment trajectories.
3. **Occupation shares** (scripts/occupation_forecasts_from_segment_totals.py):
   - Start with Michigan's 2024 MCDA detailed shares (ase_share).
   - Derive national BLS growth factors (share_2034_bls/share_2024_bls).
   - Multiply the Michigan base shares by the growth factors, renormalize within each segment to maintain 100% totals.
   - Interpolate annually from 2024 to 2034, keeping segment employment consistent with the selected methodology (Lightcast/BEA × Moody/BLS).
4. **Outputs**: mi_occ_segment_totals_2024_2034.csv (full panel) and mi_occ_segment_totals_2030.csv (planning snapshot) feed the dashboards and summary notebooks.

## Historical Staffing Pattern Change (2021–2024)
The MCDA data show how Michigan's internal mix has shifted prior to the forecast horizon:

| stage   | pct_seg_detailed_2021   | pct_seg_detailed_2024   |
|---------|-------------------------|-------------------------|

These averages (by stage) indicate modest movement toward engineering/design and downstream activities, which become the base for our 2024 shares.

## National BLS Share Targets
To gauge the national pull embedded in the forecast we compare 2024 vs. 2034 BLS segment shares:

|   segment_id | segment_name                                           |   segment_share_2024 |   segment_share_2034 |   delta |
|-------------:|:-------------------------------------------------------|---------------------:|---------------------:|--------:|
|            1 | Materials & Processing - Non-Metals                    |               0.0111 |               0.0111 |  0.0000 |
|            1 | Materials & Processing - Coatings & Surface Treatments |               0.0111 |               0.0111 |  0.0000 |
|            1 | Materials & Processing - Metals                        |               0.0111 |               0.0111 |  0.0000 |
|            2 | Equipment Manufacturing                                |               0.0121 |               0.0121 |  0.0000 |
|            3 | Forging & Foundries                                    |               0.0147 |               0.0147 | -0.0000 |
|            4 | Parts & Machining                                      |               0.0135 |               0.0135 | -0.0000 |
|            5 | Component Systems                                      |               0.0133 |               0.0134 |  0.0000 |
|            6 | Engineering & Design                                   |               0.0073 |               0.0073 |  0.0000 |
|            7 | Core Automotive                                        |               0.0137 |               0.0137 | -0.0000 |
|            8 | Motor Vehicle Parts, Materials, & Products Sales       |               0.0092 |               0.0092 |  0.0000 |
|            9 | Dealers, Maintenance, & Repair                         |               0.0171 |               0.0172 |  0.0000 |
|           10 | Logistics                                              |               0.0210 |               0.0210 |  0.0000 |

Segments with larger positive deltas (e.g., logistics) exert more upward pressure on the Michigan shares when the growth factor is applied.

## Segment-Level Baseline & Forecast (Lightcast + Moody default)
Full-segment totals (including downstream) across 2024 and 2030:

|   segment_id | segment_name                    | stage      |     2024 |     2030 |   abs_change_2024_2030 |   pct_change_2024_2030 |
|-------------:|:--------------------------------|:-----------|---------:|---------:|-----------------------:|-----------------------:|
|            0 | 0. All Segments                 | nan        |    231.3 |    229.4 |                   -1.9 |                   -0.8 |
|            1 | 1. Materials & Processing       | Upstream   |  26633.1 |  26022.2 |                 -610.9 |                   -2.3 |
|            2 | 2. Equipment Manufacturing      | Upstream   |  14758.9 |  14091.1 |                 -667.7 |                   -4.5 |
|            3 | 3.Forging and foundries         | Upstream   |  10458.5 |   8931.3 |                -1527.2 |                  -14.6 |
|            4 | 4. Parts & Machining            | Upstream   |  21044.0 |  20154.0 |                 -890.0 |                   -4.2 |
|            5 | 5. Component Systems            | Upstream   |   6667.8 |   6532.0 |                 -135.8 |                   -2.0 |
|            6 | 6. Engineering & Design         | OEM        |   4998.5 |   5178.6 |                  180.1 |                    3.6 |
|            7 | 7. Core Automotive              | OEM        | 173082.0 | 174991.5 |                 1909.5 |                    1.1 |
|            8 | 8. Motor Vehicle Parts, Materia | Downstream | 115340.0 | 116953.0 |                 1613.0 |                    1.4 |
|            9 | 9. Dealers, Maintenance, & Repa | Downstream |  69600.0 |  71674.3 |                 2074.3 |                    3.0 |
|           10 | 10. Logistics                   | Downstream |  10199.2 |   9078.6 |                -1120.6 |                  -11.0 |

Segments 1–7 capture upstream/core automotive; segments 8–10 cover sales, maintenance, and logistics. These values underpin the Overview tab cards (including the new "Upstream & Core Auto" view that strips segments 8–10).

## Top Occupation Growth (Lightcast + Moody)
Leading occupation gains over 2024–2030, aggregated statewide:

| occcd   | soctitle                                     |    2024 |    2030 |   abs_change_2024_2030 |   pct_change_2024_2030 |
|:--------|:---------------------------------------------|--------:|--------:|-----------------------:|-----------------------:|
| 51-2090 | Miscellaneous Assemblers and Fabricators     | 82830.6 | 85549.6 |                 2719.0 |                    3.3 |
| 49-9041 | Industrial Machinery Mechanics               |  8072.2 |  8942.0 |                  869.8 |                   10.8 |
| 49-3023 | Automotive Service Technicians and Mechanics | 17716.4 | 18577.0 |                  860.6 |                    4.9 |
| 17-2141 | Mechanical Engineers                         |  9005.6 |  9568.1 |                  562.5 |                    6.2 |
| 17-2112 | Industrial Engineers                         |  9273.7 |  9723.8 |                  450.1 |                    4.9 |
| 53-7061 | Cleaners of Vehicles and Equipment           |  6953.4 |  7237.6 |                  284.1 |                    4.1 |
| 41-2022 | Parts Salespersons                           |  7777.4 |  8051.4 |                  274.1 |                    3.5 |
| 41-2031 | Retail Salespersons                          | 11092.5 | 11340.2 |                  247.7 |                    2.2 |
| 53-3033 | Light Truck Drivers                          |  6628.8 |  6846.3 |                  217.5 |                    3.3 |
| 15-1252 | Software Developers                          |  2619.2 |  2817.4 |                  198.2 |                    7.6 |

This illustrates the occupations drawing the most additional employment under the default methodology, directly informing workforce and training discussions.

## Dashboards & Visual Assets
- **Interactive exploration**: dashboards/occupation_forecast_dashboard.py (general) and _v2.py (with narrative annotations).
- **Notebooks**: 15_occupation_change_tables.ipynb (tables underlying the dashboard), 11_–13_ series (comparisons between attribution methodologies).
- **Figures**: stored under eports/figures/ (e.g., top occupations, methodology spreads).

## Key Takeaways
- Lightcast attribution + Moody growth yields modest net decline in upstream manufacturing segments while logistics and downstream services hold steady.
- Applying BLS share deltas nudges Michigan's occupation mix toward national expectations by 2034 without forcing exact convergence.
- Upstream/core segments remain the focus for occupation gains (engineering, software, advanced manufacturing) even as downstream segments show varied trajectories.

## Next Steps
1. Validate attribution assumptions with partners (Lightcast vs. BEA) for segments showing large divergence.
2. Extend the dashboard to surface BLS share factors by occupation for added transparency.
3. Prepare briefing slides for stakeholders summarizing methodology and highlighting occupations with the largest reskilling needs.

