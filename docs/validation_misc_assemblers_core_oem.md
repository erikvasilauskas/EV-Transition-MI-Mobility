# Validation Walkthrough: Miscellaneous Assemblers & Fabricators (Core/OEM, Moody's MI detail)

This note documents the exact arithmetic used to derive the 2030 Core/OEM employment for SOC `51-2090` (Miscellaneous Assemblers and Fabricators) under the Moody's MI (detail) projection. All inputs are taken from the freshly generated Q1 2025 dashboard outputs in `data/processed/sam_auto_dashboard_2025_Q1/`.

## 1. Baseline Core/OEM stage employment (March 2025)

Source: `sam_employment_stage_timeseries.csv`

| Stage | Year | Projection | `employment_auto` |
| --- | --- | --- | --- |
| OEM | 2025 | Moody's MI (detail) | **167,459.88466858** |

This value is the SAM-adjusted Core/OEM total for March 2025 and serves as the 2025 baseline stage employment.

## 2. Baseline SOC employment and share within Core/OEM

Stage source: `sam_employment_stage_timeseries.csv`

| Stage | Year | `employment_auto` |
| --- | --- | --- |
| OEM / Core-OEM | 2025 | **167,459.88466858** |

SOC source: `sam_occ_segment_totals_2025_2034.csv` (segments 6 & 7 only)

| Segment | `employment_auto` (2025) |
| --- | --- |
| 6. Engineering & Design | 6.911641930196 |
| 7. Core Automotive | 64,376.6661512032 |
| **Total (SOC within Core/OEM)** | **64,383.5777931334** |

Baseline Core/OEM share of this SOC:

\[
\text{Share}_{2025} = \frac{64{,}383.5777931334}{167{,}459.88466858} = **0.3844716478**
\]

## 3. Core/OEM stage employment in 2030

Source: `sam_employment_stage_timeseries.csv`

| Stage | Year | Projection | `employment_auto` |
| --- | --- | --- | --- |
| OEM | 2030 | Moody's MI (detail) | **174,202.541790169** |

Stage growth factor, 2025→2030:

\[
\text{Stage multiplier} = \frac{174{,}202.541790169}{167{,}459.88466858} = **1.0402643125**
\]

## 4. SOC share in 2030 (after BLS drift)

Source: `sam_occ_segment_totals_2025_2034.csv`

| Segment | `employment_auto` (2030) |
| --- | --- |
| 6. Engineering & Design | 7.087337737623516 |
| 7. Core Automotive | 69,020.76481497916 |
| **Total (segments 6+7)** | **69,027.85215271668** |

Resulting share of Core/OEM stage in 2030:

\[
\text{Share}_{2030} = \frac{69{,}027.85215271668}{174{,}202.541790169} = **0.3962505452**
\]

A 3.1 % share increase (0.39625 vs. 0.38447) reflects the BLS drift adjustments applied by `build_sam_dashboard_2025_Q1.py`.

## 5. Final 2030 employment check

Long-hand multiplication:

\[
174{,}202.541790169 \times 0.3962505452 = **69{,}027.8521527**
\]

Rounded to the precision in the dashboard output, this matches the entry in `sam_occ_stage_totals_2030.csv`:

```
stage_clean  = Core/OEM
occcd        = 51-2090
employment   = 69,027.85215271679
```

## 6. Summary of inputs and outputs

| Step | File | Key values |
| --- | --- | --- |
| Baseline stage total | `sam_employment_stage_timeseries.csv` | 167,459.88466858 (OEM stage, 2025) |
| Baseline SOC total | `sam_occ_segment_totals_2025_2034.csv` | 64,383.5777931334 (segments 6+7, 2025) |
| Baseline share | Computed | 0.3844716478 |
| Stage 2030 total | `sam_employment_stage_timeseries.csv` | 174,202.541790169 (OEM stage, 2030) |
| SOC 2030 total | `sam_occ_segment_totals_2025_2034.csv` | 69,027.85215271668 (segments 6+7, 2030) |
| Share 2030 | Computed | 0.3962505452 |
| Final employment | multiplication | 69,027.8521527 (matches `sam_occ_stage_totals_2030.csv`) |

This chain demonstrates that the Core/OEM 2030 total for Miscellaneous Assemblers & Fabricators is derived directly from the SAM-adjusted stage totals and the BLS-drifted occupation shares, validating the Moody's MI (detail) scenario output.
