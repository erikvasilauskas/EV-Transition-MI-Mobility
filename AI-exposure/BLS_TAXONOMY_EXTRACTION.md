# BLS Taxonomy Mapping Extraction

## Source

- Local PDF: `mapping-employment-projections-and-onet-data.pdf`
- BLS publication: *Mapping employment projections and O*NET data*
- Extracted table: Table 3, “Step 2.A, OEWS aggregate occupations and
  weights,” PDF pages 7–8
- Source data identified by BLS: May 2016 OEWS
- Local PDF SHA-256:
  `5B1FC8782911A6A82C7F8326932B8B7F5C6083E058CD1B0D8D6275D4440F2C33`

The structured extraction is stored in
`bls_table3_taxonomy_crosswalk.csv`. It contains all source occupations and
final 2018 SOC component weights shown in Table 3, rather than only the codes
currently unmatched in this project.

## Extracted fields

- `source_ep_oews_code` and `source_ep_oews_title`: aggregate occupation in
  the 2019 EP/OEWS taxonomy;
- `target_soc_2018` and `target_soc_2018_title`: detailed 2018 SOC component;
- `final_weight`: final Step 2.A allocation weight shown by BLS;
- `pdf_table` and `pdf_page`: source location;
- `mapping_note`: relevant extraction or interpretation note.

## Validation rules

The extracted table has 20 component rows across nine source occupations.
Weights sum to 1.00 within each source occupation except `53-1047`, whose four
published weights sum to 0.99 because BLS displays rounded values. Do not
silently renormalize that row unless an analysis explicitly documents doing
so.

The table addresses these occupations appearing in the current unmatched
diagnostic:

- `13-1020` Buyers and Purchasing Agents;
- `29-2010` Clinical Laboratory Technologists and Technicians;
- `51-2028` Electrical, Electronic, and Electromechanical Assemblers;
- `53-1047` First-Line Supervisors of Transportation and Material-Moving
  Workers.

It also includes `51-2090`, the documented assembler adjustment.

The analysis applies mappings only when every component has an exposure score:

- `13-1020`, `29-2010`, and `51-2028` are applied as complete weighted
  crosswalks;
- `51-2090` is applied through its separately documented 83-percent direct
  component plus 17-percent residual imputation;
- `53-1047` is not applied because two components representing 34 percentage
  points lack exposure scores, and its displayed BLS weights sum to 0.99 after
  rounding.

The application decision and component coverage are written to
`outputs/bls_crosswalk_application_audit.csv` and
`outputs/bls_crosswalk_component_audit.csv`.

## Extraction method

No PDF skill or local PDF parser was available in the execution environment.
The table was transcribed from the machine-readable representation of the same
official BLS PDF and checked against its page and table structure. The local
PDF hash above preserves the exact source artifact used in this workspace.
