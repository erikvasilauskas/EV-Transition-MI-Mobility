# AI Exposure Analysis

This folder contains occupational employment projection inputs prepared for an
ad hoc analysis linking Michigan automotive supply-chain employment to an
occupational AI-exposure index.

## Default methodology

All copied projection files are filtered to:

- `methodology = sam_mi_moodys_mi`
- `projection_method = moodys_mi`

The source files remain unchanged under
`data/processed/sam_auto_dashboard_2024_refresh/`.

## Prepared inputs

- `sam_occ_segment_totals_2024_2034.csv`: detailed occupation-by-segment annual
  projections for 2024–2034.
- `sam_occ_segment_totals_2030.xlsx`: detailed 2030 occupation-by-segment
  snapshot with 2024 baseline and change fields.
- `sam_occ_stage_totals_2030.xlsx`: detailed 2030 occupation-by-stage snapshot
  with 2024 baseline and change fields.

The occupational AI-exposure index is stored separately as
`exposure_index_soc_2018_bls_nem_titles.xlsx`. The primary join key is the
detailed SOC code (`occcd` to `SOC_2018`), with unmatched aggregate and hybrid
codes documented for a future crosswalk decision.

## AI-exposure analysis

`analyze_ai_exposure.py` performs an exact-code merge to the 2018 SOC exposure
index and writes reproducible tables, merged datasets, diagnostics, and charts
under `outputs/`. Run it from the repository root with:

```powershell
python AI-exposure/analyze_ai_exposure.py
```

Exposure quartile `q1` is the highest-exposure quartile and `q4` is the lowest.
Aggregate or hybrid codes are assigned exposure only through a complete BLS
weighted crosswalk or the documented `51-2090` residual adjustment described
in `IMPUTATION_METHODOLOGY.md`. Other nonmatches remain in the merged data with
blank exposure measures. Summary tables report exact, crosswalked, and imputed
employment coverage, and
`outputs/unmatched_soc_diagnostic.csv` identifies the occupations still
requiring a future crosswalk or explicit imputation decision.

Segment quartile charts are produced for both 2024 and 2030. Each colored
section is expressed as a share of exposure-matched employment within the
segment, so every bar sums to 100 percent. The presentation axis label is
“Share of segment employment (%).”

The experimental 2024 national-benchmark chart adds a visually distinct “All
Industry Employment (National)” reference bar with exactly 25 percent in each
quartile. This is a constructed equal-quartile benchmark. It is not an
independently calculated national employment distribution because the supplied
exposure-index workbook does not contain national employment weights.

## BLS taxonomy crosswalk

The local BLS PDF `mapping-employment-projections-and-onet-data.pdf` is the
source for `bls_table3_taxonomy_crosswalk.csv`, a structured extraction of all
20 component mappings and weights in Table 3. Complete weighted mappings are
applied for `13-1020`, `29-2010`, and `51-2028`; `51-2090` uses its documented
residual imputation, while incomplete `53-1047` remains unmatched. See
`BLS_TAXONOMY_EXTRACTION.md` for source pages, validation rules, the local PDF
hash, application audit outputs, and extraction limitations.
