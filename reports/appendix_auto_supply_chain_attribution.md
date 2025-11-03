# Appendix X. Automotive Supply-Chain Attribution Methodology

## Purpose

This appendix describes the data sources and processing steps used to
derive automotive supply-chain attribution shares for Michigan and the
United States. The resulting `auto_share_of_output` values are used as a
proxy for the share of industry employment embedded in the mobility
supply chain. For example, if 30 percent of an industry’s output in
Michigan flows to automotive buyers, we assume that 30 percent of that
industry’s employment supports automotive activity.

## Data Sources

| Data set | Description | Repository path |
| --- | --- | --- |
| Michigan SAM | 2022 Social Accounting Matrix with Commodity Use/Make tables | `data/raw/SAM.csv` |
| US SAM | National SAM in the same structure as the Michigan file | `data/raw/SAM_US_same_structure.csv` |
| IMPLAN → NAICS bridge | Maps IMPLAN 528 industries to six-digit NAICS with employment weights | `data/raw/Bridge_2022NaicsToImplan528_AllDescriptions.xlsx` |
| IMPLAN aggregated mapping | Groups IMPLAN industries into broader NAICS aggregates | `data/raw/Implan528toAggregated2022Naics.xlsx` |
| Mobility supply-chain lookup | Defines the 38 NAICS industries, segments, and stages used in the EV analysis | `data/lookups/segment_assignments.csv` |

## Methodology Overview

The workflow is implemented in `scripts/build_sam_auto_shares_v2.py` and
its CLI wrapper `scripts/build_sam_auto_shares_cli.py`. The steps are:

1. **Load and clean the SAM.** Commodity Use (intermediate purchases) and
   Commodity Make (production) tables are required. Values and industry
   codes are converted to numeric types.
2. **Identify automotive purchasers.** By default, SAM industries 324–336
   (fuels, chemicals, plastics, metals, machinery, electrical equipment,
   and motor vehicles) form the automotive purchasing set. The CLI allows
   overrides via `--auto-codes`.
3. **Compute commodity-level attribution.** For each commodity, total
   intermediate demand and the portion purchased by automotive industries
   are summed, yielding `commodity_auto_share` values.
4. **Allocate to producing industries.** Commodity-level automotive demand
   is distributed to producing industries in proportion to their make
   shares, producing automotive-attributed output by industry. Dividing by
   total industry output provides `auto_share_of_output`.
5. **Crosswalk to NAICS.** Automotive shares are spread across NAICS6
   using the IMPLAN bridge, rolled up to NAICS4, and merged with the
   38-industry mobility lookup. Aggregated NAICS outputs are produced for
   higher-level reporting.
6. **Labelled outputs.** When the CLI is invoked with `--label`, the
   outputs are suffixed (e.g., `_us`) so Michigan and national results can
   coexist.

## Key Outputs

| File | Description |
| --- | --- |
| `data/intermediate/sam_naics_shares_v2/sam_auto_implan_shares.csv` | Michigan IMPLAN industry output, automotive-attributed output, and share. |
| `data/intermediate/sam_naics_shares_v2/sam_auto_implan_shares_us.csv` | U.S. version of the same metrics. |
| `data/intermediate/sam_naics_shares_v2/sam_auto_naics4_mobility38.csv` | Michigan NAICS4 shares aligned to the mobility universe. |
| `data/intermediate/sam_naics_shares_v2/sam_auto_naics4_mobility38_us.csv` | U.S. NAICS4 shares for the mobility universe. |
| `data/intermediate/sam_naics_shares_v2/sam_auto_naics6_shares{_us}.csv` | Detailed six-digit NAICS allocations. |
| `data/intermediate/sam_naics_shares_v2/sam_auto_naics_aggregated_shares{_us}.csv` | Aggregated NAICS groupings. |

## Employment Attribution Assumption

For both Michigan and U.S. analyses, `auto_share_of_output` is applied to
industry employment totals to estimate the number of jobs connected to
the mobility supply chain. This proportional employment attribution feeds
the employment projection pipelines and dashboard views that compare
alternative forecasting scenarios.
*** End Patch
