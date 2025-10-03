from pathlib import Path
text = Path('dashboards/occupation_forecast_dashboard_v2.py').read_text(encoding='utf-8')

def replace_block(start_marker, triple_text):
    global text
    start = text.index(start_marker)
    end = text.index("\")\n", start) + len("\")\n")
    text = text[:start] + triple_text + text[end:]

replace_block('    st.markdown("\r\n**Objectives**: Provide a quick read on how Michigan\'s automotive workforce evolves under alternative growth assumptions.',
              '    st.markdown("""\n**Objectives**: Provide a quick read on how Michigan\'s automotive workforce evolves under alternative growth assumptions.\n\n**Methods**: Each methodology blends a segment attribution source (BEA or Lightcast) with a growth path (Moody or BLS). Employment totals are aggregated across all segments for comparability.\n\n**Data Inputs**: Occupation-level forecasts generated via `scripts/occupation_forecasts_from_segment_totals.py`, seeded by MCDA staffing shares and Moody/BLS adjustments.\n\n**Use Case**: Scan for scenarios with material deviations to guide scenario planning and stakeholder communications.\n""")\n')

replace_block('    st.markdown("\r\n**Objectives**: Understand which parts of the automotive supply chain gain or lose employment.',
              '    st.markdown("""\n**Objectives**: Understand which parts of the automotive supply chain gain or lose employment.\n\n**Methods**: Segment totals reflect the selected methodologies; baseline (2024) shares stay constant per segment, while growth follows Moody/BLS rates. Segment 0 (statewide total) is intentionally excluded for clarity.\n\n**Data Inputs**: `mi_occ_segment_totals_2024_2034.csv` aggregates tied to MCDA staffing shares.\n\n**Use Case**: Compare bars to highlight sensitivity by scenario; use the detailed table to capture absolute levels for reporting.\n""")\n')

replace_block('    st.markdown("\r\n**Objectives**: Track the time path of employment under selected methodologies and connect to historical benchmarks.',
              '    st.markdown("""\n**Objectives**: Track the time path of employment under selected methodologies and connect to historical benchmarks.\n\n**Methods**: Forecast trajectories cover 2024-2034, while the extended chart joins historical QCEW data (2001 onward) with Moody/BLS growth projections for core automotive segments.\n\n**Data Inputs**: Occupation forecasts (`mi_occ_segment_totals_2024_2034.csv`) plus core series (`mi_qcew_segment_employment_timeseries_coreauto_extended_compare.csv`).\n\n**Use Case**: Diagnose inflection points, validate reasonableness against history, and communicate long-run trends to partners.\n""")\n')

replace_block('    st.markdown("\r\n**Objectives**: Dive into occupation-level stories to support talent, training, and education conversations.',
              '    st.markdown("""\n**Objectives**: Dive into occupation-level stories to support talent, training, and education conversations.\n\n**Methods**: Occupation forecasts inherit segment totals, MCDA staffing shares, and BLS shift adjustments. Methodology filters expose sensitivities, while the table consolidates change metrics.\n\n**Data Inputs**: Detailed SOC-level outputs from `mi_occ_segment_totals_2024_2034.csv`.\n\n**Use Case**: Identify high-growth or at-risk occupations, share with workforce boards, and target reskilling strategies.\n""")\n')

replace_block('    st.markdown("\r\n**Objectives**: Provide transparent access to datasets, lineage, and documentation supporting the forecasts.',
              '    st.markdown("""\n**Objectives**: Provide transparent access to datasets, lineage, and documentation supporting the forecasts.\n\n**Methods**: All files derive from reproducible scripts in the repository; exports retain segment, methodology, and occupation metadata for downstream analysis.\n\n**Data Inputs**: Key processed CSVs and Python scripts noted below.\n\n**Use Case**: Enable collaborators and clients to download, audit, and integrate the data into their own tools.\n""")\n')

text = text.replace('� &Delta;', '&Delta;')
text = text.replace('�', '')

Path('dashboards/occupation_forecast_dashboard_v2.py').write_text(text, encoding='utf-8')
