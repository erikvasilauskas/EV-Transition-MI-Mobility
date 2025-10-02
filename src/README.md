# Source Code Modules

This directory is designated for **reusable Python modules** that encapsulate common data processing, analytical, and visualization logic. By packaging frequently-used functions here, notebooks remain concise and focused on exploratory analysis or presentation.

## Current Status

**Note**: This directory currently contains placeholder structure only. Most analytical code currently resides in standalone scripts in `scripts/` directory. Future refactoring will migrate common functions into these modules to improve code reusability and maintainability.

## Intended Module Structure

### [data_processing/](data_processing/)
ETL (Extract, Transform, Load) routines for raw datasets.

**Purpose**: Standardize data ingestion, cleaning, and transformation logic that's shared across multiple analyses.

**Planned Modules**:
- `loaders.py` - Functions to read and standardize raw data files (QCEW, Moody's, BLS, MCDA)
- `cleaning.py` - Shared routines for handling NAICS/SOC re-coding, suppression flags, missing data
- `segment_mapping.py` - Utilities to map industries to 10 supply-chain segments
- `time_series.py` - Functions for constructing and validating time series data
- `attribution.py` - Apply auto-industry attribution shares (BEA, Lightcast)

**Migration Path**: Extract common patterns from `scripts/process_*.py` files.

### [analysis/](analysis/)
Business logic for calculating metrics, aggregating data, and generating analytical outputs.

**Purpose**: Encapsulate domain-specific calculations that define "what" the analysis computes (as opposed to "how" data is loaded or displayed).

**Planned Modules**:
- `segment_profiles.py` - Build occupational mix summaries for each segment
- `comparisons.py` - Compare Michigan vs. US staffing patterns, segments vs. baselines
- `indicators.py` - Composite metrics (concentration indices, location quotients, growth estimates)
- `forecasting.py` - Apply growth rates, extend time series, generate projections
- `aggregations.py` - Weight and aggregate NAICS-level data to segments and stages

**Migration Path**: Extract analytical logic from `scripts/apply_*.py` and `scripts/compute_*.py` files.

### [visualization/](visualization/)
Charting helpers, styling conventions, and report generation utilities.

**Purpose**: Standardize visual outputs and reduce code duplication in notebooks.

**Planned Modules**:
- `charts.py` - Standard chart types (time series, comparisons, distributions)
- `styling.py` - Color palettes, fonts, figure sizes for consistent branding
- `tables.py` - Formatted tables for reports (HTML, LaTeX, markdown)
- `exports.py` - Save figures/tables with consistent naming and metadata

**Migration Path**: Extract plotting code from notebooks `08_*.ipynb` through `13_*.ipynb`.

## Why Modularize?

### Benefits of Refactoring into `src/`

1. **Code Reusability**: Write once, use in multiple notebooks and scripts
2. **Easier Testing**: Isolated functions are easier to unit test than notebook cells
3. **Version Control**: Changes to logic are tracked separately from exploratory analysis
4. **Documentation**: Module-level docstrings provide centralized reference
5. **Collaboration**: Multiple analysts can work on different modules without merge conflicts in notebooks
6. **Maintenance**: Bug fixes in one place propagate to all uses

### Current Approach (Scripts)

Currently, most logic resides in `scripts/` directory as standalone executables. This works well for:
- One-off data processing tasks
- Pipeline steps that run sequentially
- Quick prototyping and iteration

### When to Migrate to `src/`

Consider moving code to `src/` when:
- Same function is copy-pasted across 3+ scripts/notebooks
- Function is stable and unlikely to change frequently
- Logic is complex enough to benefit from unit testing
- Code is used by external collaborators who need documentation

## Usage Pattern (Once Implemented)

```python
# In a notebook or script
import sys
sys.path.append('../src')  # or absolute path

from data_processing.loaders import load_qcew, load_moodys
from analysis.aggregations import aggregate_by_segment
from visualization.charts import plot_time_series

# Use the modules
qcew = load_qcew('data/raw/MI-QCEW-38-NAICS-2001-2024.xlsx')
segment_ts = aggregate_by_segment(qcew, weights='employment_qcew_2024')
fig = plot_time_series(segment_ts, title='Michigan Auto Segments 2001-2024')
```

## Package Installation (Future)

Once modules are implemented, this could be converted to an installable package:

```bash
# From repository root
pip install -e .  # Editable install for development
```

Requires adding:
- `setup.py` or `pyproject.toml` in repository root
- `__init__.py` files in each module directory
- Package metadata (version, dependencies, author)

## Migration Priority

Suggested order for refactoring existing scripts into modules:

### Phase 1: Core Data Loading
Extract from `scripts/process_*.py`:
- QCEW loading and normalization
- Moody's time series parsing
- Segment assignment lookups

**Impact**: High - used by nearly all analyses

### Phase 2: Forecasting Logic
Extract from `scripts/apply_*.py`:
- Growth rate application
- Time series extension
- Attribution methodology implementations

**Impact**: High - core to projection analyses

### Phase 3: Aggregation Functions
Extract from multiple scripts:
- NAICS → Segment rollups
- Segment → Stage rollups
- Employment weighting logic

**Impact**: Medium - standardizes key calculations

### Phase 4: Visualization
Extract from notebooks:
- Standa rd time series plots
- Comparison charts
- Styling conventions

**Impact**: Medium - improves consistency

### Phase 5: Analytical Metrics
Extract from `scripts/compare_*.py`:
- Staffing pattern comparisons
- Diagnostic calculations
- Statistical summaries

**Impact**: Low - less frequently reused

## Development Guidelines

When adding code to `src/` modules:

### Function Design
- **Single Responsibility**: Each function should do one thing well
- **Type Hints**: Use Python type hints for parameters and returns
- **Docstrings**: Follow NumPy or Google docstring conventions
- **Error Handling**: Validate inputs and provide informative error messages

### Documentation
- Module-level docstring explaining purpose and scope
- Function-level docstrings with parameters, returns, examples
- Inline comments for complex logic only

### Testing
- Write unit tests in `tests/` directory (to be created)
- Test edge cases: empty data, missing values, wrong types
- Use pytest for test framework

### Dependencies
- Minimize external dependencies beyond core stack (pandas, numpy, matplotlib)
- Document any additional requirements in `requirements.txt`

## Related Documentation

- [../scripts/README.md](../scripts/README.md) - Current location of most analytical code
- [../notebooks/README.md](../notebooks/README.md) - Interactive analysis using these modules
- [../docs/methodology.md](../docs/methodology.md) - Methodological context for analytical functions

## Questions?

If you're unsure whether code belongs in `src/` vs. `scripts/`:
- **One-time data processing**: Keep in `scripts/`
- **Reusable function**: Move to `src/`
- **Exploratory analysis**: Keep in `notebooks/`
- **Production ETL pipeline**: Could be either, depending on reusability

When in doubt, start in `scripts/` and refactor to `src/` once patterns emerge.
