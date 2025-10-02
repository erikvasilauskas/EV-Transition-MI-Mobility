# Documentation

This directory contains project documentation, methodological decisions, data source catalogs, and analytical assumptions that guide the EV-Transition analysis. Treat these documents as the project's narrative thread—they provide context for code decisions and help collaborators understand the rationale behind analytical choices.

## Documentation Files

### [segment_definitions.md](segment_definitions.md)
Defines the **10 automotive supply-chain segments** that structure all analysis in this project.

**Purpose**:
- Establish working names for each segment
- Document which industries (NAICS codes) belong to each segment
- Capture stage assignments (Upstream, OEM, Downstream)
- Record data quality caveats specific to segments

**Current Status**: Template structure in place. Needs population with actual segment definitions from `data/lookups/segment_assignments.csv`.

**Update Frequency**: As needed when segment boundaries change or new industries are added.

**Key Users**: Anyone performing segment-level analysis, creating visualizations, or explaining results to stakeholders.

### [data_sources.md](data_sources.md)
Comprehensive **catalog of all data inputs** used in the analysis, including access methods, licensing, and refresh schedules.

**Currently Documented Sources**:
1. **QCEW** (BLS) - Michigan employment by NAICS
2. **OEWS** (BLS/MCDA) - Occupational staffing patterns
3. **Moody's Analytics** - Long-range employment/GDP forecasts
4. **BLS Employment Projections** - US industry×occupation matrices
5. **MCDA** - Michigan segment staffing patterns

**For Each Source, Documents**:
- Provider organization
- Access method (download, API, partner provision)
- Refresh cadence
- License/terms of use
- Primary analytical use case

**Update Frequency**: When new data sources are added or access methods change.

**Key Users**: Anyone acquiring data, updating pipelines, or ensuring licensing compliance.

### [methodology.md](methodology.md)
**Living log of methodological decisions** made throughout the project lifecycle.

**Structure**:

1. **Key Research Questions**
   - What occupational differences exist across segments?
   - Which industries anchor each segment?
   - How does Michigan compare to national benchmarks?

2. **Planned Approach**
   - High-level analytical workflow
   - Data integration strategy
   - Aggregation methods

3. **Open Decisions**
   - Unresolved methodological questions
   - Alternatives under consideration
   - Sensitivity analyses needed

4. **Decision Log** (dated entries)
   - Records when decisions were finalized
   - Rationale for choices made
   - Impact on downstream analysis

**Current Decision Log**:
- **2025-09-30**: Adopted BLS 2024-2034 industry×occupation matrices as US benchmark
  - Enables direct comparison with Michigan OEWS patterns
  - Addresses BLS data access constraints
  - Requires NAICS fallback strategy for missing granular data

**Update Frequency**: Add dated entries whenever significant methodological decisions are made.

**Key Users**: Analysts explaining approach to stakeholders, researchers understanding decision context, quality assurance reviewers.

## How to Use This Documentation

### For New Team Members
Start here to understand the project:

1. **Read [segment_definitions.md](segment_definitions.md)** - Understand the 10-segment framework
2. **Review [data_sources.md](data_sources.md)** - Know where data comes from
3. **Skim [methodology.md](methodology.md)** - Learn key analytical decisions
4. **Check [../README.md](../README.md)** - See overall project objectives and workflow

### For Ongoing Analysis Work

**Before Making a Methodological Decision**:
1. Check [methodology.md](methodology.md) to see if the question has been addressed
2. Review "Open Decisions" section to see if it's a known unresolved issue
3. If making a new decision, add a dated entry to the Decision Log

**Before Adding a New Data Source**:
1. Document it in [data_sources.md](data_sources.md) with all required fields
2. Note licensing restrictions and refresh cadence
3. Update relevant scripts in `scripts/` to incorporate the new source

**When Changing Segment Definitions**:
1. Update [segment_definitions.md](segment_definitions.md) first
2. Modify `data/lookups/segment_assignments.csv` to reflect changes
3. Re-run affected ETL scripts
4. Add a dated entry to [methodology.md](methodology.md) explaining why

### For Stakeholder Communication

Use these documents to:
- Explain analytical framework (segment definitions)
- Cite data provenance (data sources)
- Defend methodological choices (methodology log)
- Ensure reproducibility (documented decisions)

## Documentation Best Practices

### Writing Style
- **Be concise**: Aim for clarity over comprehensiveness
- **Date all decisions**: Use YYYY-MM-DD format for decision log entries
- **Link to code**: Reference specific scripts that implement decisions
- **Explain trade-offs**: Document what was considered and why one approach was chosen

### Versioning
- Track changes to documentation files in git
- Add dated entries rather than editing old entries (preserves decision history)
- Use markdown for easy diffing and version control

### What Belongs Here vs. Code Comments

**In Documentation Files** (docs/):
- High-level rationale and research questions
- Data source access procedures
- Methodological choices affecting multiple scripts
- Segment/classification definitions used project-wide

**In Code Comments** (scripts/, src/):
- Implementation details
- Technical assumptions in specific functions
- Parameter explanations
- Bug fixes and edge cases

**Rule of Thumb**: If it affects "what" or "why," document it here. If it explains "how," comment it in code.

## Maintenance Schedule

### Monthly
- Review "Open Decisions" in [methodology.md](methodology.md)
- Update [data_sources.md](data_sources.md) if access methods change
- Ensure recent methodological choices are documented

### Quarterly
- Audit decision log for missing entries
- Validate that [segment_definitions.md](segment_definitions.md) matches current `segment_assignments.csv`
- Review documentation for outdated information

### Annually
- Comprehensive review of all documentation
- Archive deprecated approaches or superseded decisions
- Update data source refresh schedules for new calendar year

## Related Documentation

### Repository-Level
- [../README.md](../README.md) - Project overview and workflow
- [../data/README.md](../data/README.md) - Data pipeline and file structure
- [../notebooks/README.md](../notebooks/README.md) - Notebook descriptions and execution order

### External References
- BLS QCEW methodology: <https://www.bls.gov/cew/publications/employment-and-wages-annual-averages/home.htm>
- BLS Employment Projections methodology: <https://www.bls.gov/emp/documentation/projections-methods.htm>
- NAICS structure: <https://www.census.gov/naics/>

## Contributing to Documentation

When adding or updating documentation:

1. **Check existing structure** - Add content to existing files when possible
2. **Use consistent formatting** - Follow markdown conventions in existing docs
3. **Link liberally** - Connect related documentation and reference code
4. **Date significant changes** - Especially in methodology log
5. **Keep it current** - Update docs when code or approach changes

If you need to create a new documentation file:
- Follow the naming pattern: `lowercase_with_underscores.md`
- Add a section to this README explaining its purpose
- Link to it from other relevant documentation

## Questions About Documentation?

If documentation is unclear or missing:
1. Check if answer exists in code comments or commit messages
2. Review executed notebooks for analytical context
3. Create an issue or discussion to get missing information documented

**Remember**: Good documentation enables reproducible research and efficient collaboration. When in doubt, document it!
