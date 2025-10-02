# Occupation Forecast Data Flow

## Key Clarification: We Don't Aggregate to Segments

A common misconception is that the occupation forecast script aggregates occupational employment to get segment totals. **This is NOT the case**.

Instead, the script **distributes** QCEW-based segment totals across occupations using staffing pattern shares.

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ SEGMENT EMPLOYMENT TOTALS (Source: QCEW + Forecasts)           │
│                                                                 │
│ Files:                                                          │
│  - mi_qcew_segment_employment_timeseries_bea_extended_moody.csv│
│  - mi_qcew_segment_employment_timeseries_bea_extended_bls.csv  │
│  - (+ Lightcast versions)                                       │
│                                                                 │
│ These are NAICS-based aggregations from:                        │
│  1. Historical QCEW data (2001-2024)                           │
│  2. Applied growth rates (2024-2034)                           │
│  3. Attribution adjustments (BEA or Lightcast)                 │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ Segment totals provided as inputs
                         │
                         v
┌─────────────────────────────────────────────────────────────────┐
│ OCCUPATIONAL SHARES (Source: MCDA + BLS)                        │
│                                                                 │
│ MCDA 2024 Base:                                                 │
│  - "Machinists are 2.5% of Materials & Processing segment"    │
│  - Based on Michigan OEWS data                                 │
│  - Detailed occupations only (no summaries)                    │
│                                                                 │
│ Adjustments:                                                    │
│  1. Auto attribution discount (BEA or Lightcast shares)        │
│  2. Occupational shift trends (BLS 2024-2034 changes)          │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ Shares applied to totals
                         │
                         v
┌─────────────────────────────────────────────────────────────────┐
│ OCCUPATION-LEVEL FORECASTS (Output)                            │
│                                                                 │
│ Formula:                                                        │
│  Occupation Employment (year, segment) =                        │
│    Segment Total (year) × Occupation Share (year)              │
│                                                                 │
│ Result:                                                         │
│  Employment by occupation, segment, year, methodology           │
│                                                                 │
│ Validation:                                                     │
│  Sum of occupations = Segment total (within rounding)          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Detailed Example: Machinists in Materials & Processing (2030)

### Input 1: Segment Total (from QCEW forecast)

**File**: `mi_qcew_segment_employment_timeseries_bea_extended_moody.csv`

```
segment_id, segment_name, year, employment_qcew
1, Materials & Processing, 2030, 65000
```

This came from:
1. 2024 QCEW actual employment for NAICS codes in Segment 1
2. BEA auto attribution applied to each NAICS
3. Moody's growth rates applied through 2030

---

### Input 2: Occupational Share (from MCDA + adjustments)

**Base MCDA 2024**:
```
segment, occupation_code, occupation_title, employment
"1. Materials & Processing", "51-4041", "Machinists", 1,800
```

**Segment 1 total employment in MCDA 2024**: 72,030

**Base share**: 1,800 / 72,030 = 2.50%

**Auto attribution adjustment** (BEA):
- Segment 1 weighted BEA auto share: 0.45 (45% automotive)
- Adjusted share: 2.50% × 0.45 = 1.125%

**Occupational shift** (BLS 2024-2034):
- BLS projects Machinists decline from 2.5% to 2.0% of manufacturing
- 2030 interpolated share: 2.25% (6 years into 10-year decline)
- Applied auto-adjusted: 1.125% × (2.25 / 2.50) = 1.013%

---

### Output: Occupation Forecast

```
Machinists (51-4041) in Segment 1 (BEA × Moody's), 2030:
  65,000 × 1.013% = 659 jobs
```

**Key point**: We used the QCEW-based segment total (65,000) and applied the occupation share to it. We did NOT add up occupations to get 65,000.

---

## Why This Approach?

### Pros
1. **Preserves QCEW accuracy**: Segment totals are grounded in actual employment data
2. **Avoids error compounding**: We don't introduce error by aggregating 400+ occupations
3. **Consistent with segment forecasts**: Uses same totals as segment-level analysis
4. **Enables validation**: Sum of occupations MUST equal segment total (easy to check)

### Cons
1. **Assumes shares capture full employment**: If MCDA missing occupations, totals won't match
2. **Share shifts limited to BLS data**: Can't model Michigan-specific occupational trends
3. **Attribution applied uniformly**: Same auto share used across all occupations in segment

---

## Avoiding Double-Counting: Occupation Hierarchy

The MCDA data has occupational summaries that must be filtered out:

```
00-0000   "Total all occupations"          ← GRAND TOTAL (exclude)
  │
  ├─ 11-0000   "Management Occupations"    ← MAJOR GROUP (exclude)
  │    │
  │    ├─ 11-1000   "Top Executives"       ← BROAD GROUP (exclude)
  │    │    │
  │    │    ├─ 11-1011   "Chief Executives"        ← DETAILED (USE)
  │    │    └─ 11-1021   "General Managers"        ← DETAILED (USE)
  │    │
  │    └─ 11-3000   "Operations Managers"  ← BROAD GROUP (exclude)
  │         └─ 11-3051   "Industrial Prod Mgrs"    ← DETAILED (USE)
  │
  └─ 13-0000   "Business Operations"       ← MAJOR GROUP (exclude)
       └─ 13-1000   "Business Specialists" ← BROAD GROUP (exclude)
            ├─ 13-1051   "Cost Estimators"         ← DETAILED (USE)
            └─ 13-1071   "HR Specialists"          ← DETAILED (USE)
```

**Script filtering**:
```python
# Line 43: Filter to detailed occupations only
mcda_2024 = mcda_2024[mcda_2024['occ_level'] == 'detailed'].copy()
```

This ensures we only use leaf-level occupations. Summing these WILL equal the "00-0000 Total" (within rounding).

---

## Validation: Do Occupations Sum to Segments?

The script includes built-in validation:

```python
# Lines 355-391: Validation check
for methodology in ['bea_Moody', 'bea_BLS', 'lightcast_Moody', 'lightcast_BLS']:
    # Sum occupation forecasts by segment
    occ_totals_2030 = forecast_2030.groupby('segment_id')['employment'].sum()

    # Load original segment forecasts
    seg_forecast_2030 = ... (from QCEW forecast file)

    # Compare
    diff_pct = abs(occ_total - seg_total) / seg_total * 100
```

**Expected result**: <5% difference (small discrepancies from rounding acceptable)

**If >5% difference**:
- Missing occupations in MCDA data
- Filtering error (excluded wrong occupations)
- Share calculation bug
- BLS shift data misalignment

---

## Data Sources Summary

| Component | Source | Role in Forecast |
|-----------|--------|------------------|
| **Segment totals** | QCEW (via forecast scripts) | **Determines total employment** |
| **Occupational shares** | MCDA 2024 base | **Distributes totals across occupations** |
| **Auto attribution** | BEA or Lightcast | **Adjusts shares for auto-only** |
| **Occupational shifts** | BLS 2024-2034 projections | **Updates shares over time** |

---

## Common Misconceptions

### ❌ WRONG: "We aggregate occupations to get segment totals"

**Why it's wrong**:
- Segment totals come from QCEW NAICS aggregation (already done in forecast scripts)
- Adding up occupations would introduce compounding errors
- Would ignore actual employment data

### ✓ CORRECT: "We distribute segment totals across occupations"

**Why it's right**:
- Segment totals are fixed inputs (from QCEW)
- Occupational shares allocate that total
- Ensures occupations sum to observed segment employment

---

### ❌ WRONG: "MCDA employment numbers are the forecast"

**Why it's wrong**:
- MCDA gives 2024 base year shares, not forecasts
- MCDA totals don't match QCEW exactly (different sources)
- We use MCDA for distribution, not totals

### ✓ CORRECT: "MCDA shares applied to QCEW-based totals produce the forecast"

**Why it's right**:
- MCDA tells us occupational mix (shares)
- QCEW tells us total employment (levels)
- BLS tells us how mix changes over time
- Combined, they produce occupation-specific forecasts

---

## Implications for Analysis

### When interpreting results:

1. **Segment totals are exogenous**: Occupation forecasts inherit segment growth rates
2. **Within-segment shifts are endogenous**: BLS occupational trends affect distribution
3. **Total automotive employment**: Already determined by segment forecasts
4. **Occupation-specific growth**: Combination of segment growth + occupational shift

### Example interpretation:

**"Machinists are forecast to decline 15% from 2024-2030"**

This could mean:
- Segment 1 declining 10% (segment effect)
- Machinists declining 5% within segment (occupational shift effect)
- Combined: 15% decline

Or:
- Segment 1 growing 5% (segment effect)
- Machinists declining 20% within segment (strong automation)
- Combined: 15% decline

**Key**: Decompose occupation change into segment effect vs. shift effect for proper interpretation.

---

## Related Documentation

- [methodology.md](methodology.md) - Decision log
- [occupation_forecast_methodology.md](occupation_forecast_methodology.md) - Full technical details
- [data/README.md](../data/README.md) - Data pipeline overview
- [scripts/README.md](../scripts/README.md) - Script execution order

---

**Last Updated**: October 2025
