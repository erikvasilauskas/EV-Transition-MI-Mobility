# SAM-Based Automotive Supply-Chain Attribution

This document explains how the repository converts Social Accounting
Matrix (SAM) transactions into automotive supply-chain attribution
shares. The workflow supports both the Michigan SAM
(`data/raw/SAM.csv`) and the national SAM with matching structure
(`data/raw/SAM_US_same_structure.csv`). The main logic lives in
`scripts/build_sam_auto_shares_v2.py`, with a command-line wrapper
`scripts/build_sam_auto_shares_cli.py` for labelled or alternative runs.

## Source Data

- **SAM inputs**
  - Michigan: `data/raw/SAM.csv`
  - United States: `data/raw/SAM_US_same_structure.csv`
  - Required fields: `PayingCode`, `PayingDescription`, `ReceivingCode`,
    `ReceivingDescription`, `TransferDescription`, `Value`
  - Required transfer descriptions: `Commodity Use`, `Commodity Make`
- **IMPLAN → NAICS bridge** – `data/raw/Bridge_2022NaicsToImplan528_AllDescriptions.xlsx`
  (distributes IMPLAN industries across 6-digit NAICS using employment weights)
- **Aggregated IMPLAN mapping** – `data/raw/Implan528toAggregated2022Naics.xlsx`
  (groups IMPLAN industries into broader NAICS aggregates)
- **Mobility supply-chain lookup** – `data/lookups/segment_assignments.csv`
  (defines the 38 NAICS industries, segments, and stages used downstream)

## Processing Workflow

Implemented in `build_sam_auto_shares_v2.py` / `build_sam_auto_shares_cli.py`.

1. **Load and clean the SAM**
   - Trim column names and coerce `Value`, `PayingCode`, and `ReceivingCode` to numeric.
   - The scripts require the SAM to include both Commodity Use (intermediate purchases)
     and Commodity Make (production) tables.

2. **Identify automotive purchasers**
   - Default SAM industry set: codes 324–336 (fuels, chemicals, plastics, metals,
     machinery, electrical equipment, motor vehicles, etc.).
   - Override with `--auto-codes` on the CLI if a different buyer set is needed.

3. **Commodity-level attribution**
   - Filter `Commodity Use` transactions, compute total intermediate demand per commodity,
     and sum the subset purchased by the automotive industries.
   - Derive `commodity_auto_share = auto_use / total_use`.

4. **Allocate to producing industries**
   - For each commodity, read `Commodity Make` rows to determine the share produced by each industry.
   - Multiply the commodity’s automotive demand by the industry’s make share to obtain
     automotive-attributed output for that industry.
   - Aggregate by industry to produce `auto_attributed_output`, `total_industry_output`,
     and `auto_share_of_output = auto_attributed_output / total_industry_output`.

5. **Crosswalk to NAICS**
   - Join the IMPLAN → NAICS bridge to distribute industry shares to NAICS6 using the bridge weights.
   - Roll up to NAICS4 and merge with the 38-industry mobility lookup to create the analysis universe.
   - Produce an aggregated NAICS view using the IMPLAN aggregation file for coarser reporting.

6. **Labelled outputs**
   - The CLI accepts `--label` to append a suffix (e.g., `_us`) to output filenames, allowing
     Michigan and US results to coexist in `data/intermediate/sam_naics_shares_v2/`.

## Outputs

All files below live in `data/intermediate/sam_naics_shares_v2/` and may include a `_us`
suffix when the national SAM is processed.

| File | Description |
| --- | --- |
| `sam_auto_commodity_shares{label}.csv` | Commodity demand attributed to automotive purchasers (Commodity Use/Make only). |
| `sam_auto_implan_shares{label}.csv` | IMPLAN industry totals, automotive-attributed output, and share. |
| `sam_auto_naics6_shares{label}.csv` | Automotive shares distributed to NAICS6 via IMPLAN bridge weights. |
| `sam_auto_naics4_mobility38{label}.csv` | NAICS4 shares aligned with the 38-industry mobility lookup. |
| `sam_auto_naics_aggregated_shares{label}.csv` | Aggregated NAICS groupings derived from the IMPLAN aggregation file. |

`{label}` is blank for Michigan and `_us` for the national run (or any custom label supplied).

## Reproducibility

```bash
# Michigan baseline
python scripts/build_sam_auto_shares_v2.py

# National SAM (same structure as Michigan)
python scripts/build_sam_auto_shares_cli.py \
  --sam-path data/raw/SAM_US_same_structure.csv \
  --label us
```

Additional CLI options:

- `--auto-codes` – override the default automotive purchasing set.
- `--bridge-path`, `--agg-path`, `--lookup-path` – point to alternate mapping files.
- `--output-dir` – write results to a different destination.

## Employment Attribution Assumption

Downstream analyses treat the SAM-derived `auto_share_of_output` values as proxies for
automotive employment shares. If 30 percent of an industry’s output is sold to mobility
buyers, we assume roughly 30 percent of its employment supports the mobility supply chain.
These proportions feed the employment attribution and projection workflows elsewhere in the repository.
