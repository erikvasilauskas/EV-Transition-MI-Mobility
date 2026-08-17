# Occupational Exposure Imputation Methodology

## Scope

The AI-exposure analysis uses exact 2018 SOC matches wherever possible. One
material exception is employment code `51-2090`, **Miscellaneous Assemblers and
Fabricators**, which does not have a direct record in the supplied exposure
index but represents a large share of Michigan automotive employment.

No other unmatched occupation is currently imputed. Separate complete BLS
weighted crosswalks are applied to `13-1020`, `29-2010`, and `51-2028`; these
do not require residual imputation because all their components have exposure
scores.

## BLS taxonomy basis

The U.S. Bureau of Labor Statistics taxonomy-mapping methodology decomposes
`51-2090` into:

- 83 percent `51-2092`, Team Assemblers;
- 17 percent `51-2099`, Assemblers and Fabricators, All Other.

Source: BLS, *Mapping employment projections and O*NET data*, Table 3:
https://www.bls.gov/opub/mlr/2021/article/pdf/mapping-employment-projections-and-onet-data.pdf

The exposure index contains `51-2092` but does not contain the residual
occupation `51-2099`.

## Applied estimate

For quartile analysis, `51-2090` is assigned to `q4`, the lowest exposure
quartile. For continuous analysis, its central score is calculated as:

```text
0.83 * exposure score for 51-2092
+ 0.17 * median score of the other available 51-20xx assembler/fabricator occupations
```

Sensitivity bounds replace the residual median with the minimum and maximum
scores among the same donor occupations. The central and bound scores are then
converted to percentiles by interpolation against the supplied exposure
index's score-percentile distribution. Percentiles and quartile numbers are
not averaged.

The generated values and inputs are written to
`outputs/exposure_imputation_audit.csv` and to the `imputation_audit` sheet in
`outputs/ai_exposure_analysis_tables.xlsx`.

## Output flags

Merged files retain the following audit fields:

- `exposure_exact_match`: direct SOC match to the exposure index;
- `exposure_crosswalked`: exposure derived through the BLS Table 3 mapping;
- `exposure_mapping_method`: complete or residual-imputed crosswalk method;
- `exposure_imputed`: score supplied by this documented method;
- `exposure_imputation_method`: named method used;
- `exposure_match`: either exact or usable imputed exposure;
- lower and upper score and percentile sensitivity fields.

Summary coverage counts exact and imputed employment as covered. The unmatched
diagnostic therefore reports only the remaining occupations without either a
direct score or this documented imputation.
