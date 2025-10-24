# SAM-Based Automotive Supply-Chain Attribution

This note documents how the SAM-derived outputs (especially
`data/intermediate/sam_auto_naics_shares.csv`) are generated from the
raw social accounting matrix (`data/raw/SAM.csv`).

## Source Data

- **Social Accounting Matrix** - `data/raw/SAM.csv`
  - Fields: `PayingCode`, `PayingDescription`, `ReceivingCode`,
    `ReceivingDescription`, `TransferCode`, `TransferDescription`, `Value`
  - Key transfer types:
    - `Commodity Use`: intermediate demand by industries for commodities
    - `Commodity Make`: commodity output supplied by producing industries
- **BEA Make Table** - `data/raw/IOMake_Before_Redefinitions_PRO_Detail.xlsx`
  (sheet `2017`) to link SAM/BEA industries to NAICS prefixes
- **Mobility supply-chain lookup** - `data/lookups/segment_assignments.csv`
  containing the 38 target NAICS industries and segment metadata

## Processing Workflow

Implemented in `scripts/analyze_sam_auto_supply_chain.py`.

1. **Load and clean the SAM**
   - Strip whitespace from column names and coerce `Value` to numeric.

2. **Identify automotive purchasing industries**
   - Default list: SAM industries 324-336 (motor vehicles, bodies,
     transmissions, interiors, etc.). The list is overrideable through
     the `--auto-codes` argument.

3. **Aggregate commodity demand**
   - Filter `Commodity Use` rows.
   - For each commodity (`ReceivingCode`), compute total demand across
     all industries and the subset purchased by the automotive list.
   - Derive `auto_share = auto_demand / total_demand`.
   - Output: `sam_auto_commodity_shares.csv`.

4. **Allocate commodity demand to producing industries**
   - Filter `Commodity Make` rows.
   - For each commodity (`PayingCode`), compute the share supplied by
     each industry (`make_share = industry value / total commodity output`).
   - Multiply `make_share` by the commodity-level `auto_demand` to obtain
     the portion of each industry's output sold to automotive buyers.
   - Sum by industry to get `auto_attributed_output` and retain each
     industry's total output (`total_industry_output`).
   - Compute `auto_share_of_output = auto_attributed_output / total_industry_output`.
   - Output: `sam_auto_industry_shares.csv`.

5. **Crosswalk to four-digit NAICS**
   - Use the BEA make-table metadata to map each SAM industry description
     to a BEA code and leading four-digit NAICS.
   - Merge the SAM industry results with the crosswalk on description.
   - Aggregate `auto_attributed_output` and `total_industry_output`
     by NAICS and recompute `auto_share_of_output`.

6. **Restrict to the 38 mobility NAICS**
   - Join the NAICS-level results to `segment_assignments.csv`.
   - Fill missing industries with zeros so every target NAICS appears,
     even if the SAM yields no automotive demand.
   - Output: `sam_auto_naics_shares.csv`, which carries segment
     metadata plus automotive metrics.

## Outputs

| File | Purpose |
| --- | --- |
| `data/intermediate/sam_auto_commodity_shares.csv` | Commodity demand totals vs. automotive purchases |
| `data/intermediate/sam_auto_industry_shares.csv` | Industry-level automotive-attributed output and share |
| `data/intermediate/sam_auto_naics_shares.csv` | NAICS-level automotive attribution aligned with mobility segments |

## Reproducibility

Run the script from the repository root (inside the desired Python environment):

```bash
python scripts/analyze_sam_auto_supply_chain.py
```

Optional arguments:

- `--sam-path` to override the SAM input
- `--make-table-path` to use an alternate BEA make table
- `--auto-codes` to supply a custom list of SAM industry codes
- `--output-dir` to write the outputs elsewhere
