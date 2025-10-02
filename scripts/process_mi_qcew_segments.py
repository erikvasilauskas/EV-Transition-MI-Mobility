# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

import pandas as pd

RAW_QCEW_PATH = Path('data/raw/MI-QCEW-38-NAICS-2001-2024.xlsx')
SEGMENT_LOOKUP_PATH = Path('data/lookups/segment_assignments.csv')

SEGMENT_OUTPUT = Path('data/interim/mi_qcew_segment_employment_timeseries.csv')
STAGE_OUTPUT = Path('data/interim/mi_qcew_stage_employment_timeseries.csv')
SEGMENT_PROCESSED_OUTPUT = Path('data/processed/mi_qcew_segment_employment_timeseries.csv')
STAGE_PROCESSED_OUTPUT = Path('data/processed/mi_qcew_stage_employment_timeseries.csv')
RAW_LONG_OUTPUT = Path('data/interim/mi_qcew_naics_employment_timeseries.csv')

SEGMENT_LABELS = {
    1: '1. Materials & Processing',
    2: '2. Equipment Manufacturing',
    3: '3. Forging & Foundries',
    4: '4. Parts & Machining',
    5: '5. Component Systems',
    6: '6. Engineering & Design',
    7: '7. Core Automotive',
    8: '8. Motor Vehicle Parts, Materials, & Products Sales',
    9: '9. Dealers, Maintenance, & Repair',
    10: '10. Logistics',
}


def load_qcew() -> pd.DataFrame:
    wide = pd.read_excel(RAW_QCEW_PATH, skiprows=3)
    wide = wide.rename(columns={'Series ID': 'series_id'})
    year_columns = {}
    for col in wide.columns:
        if isinstance(col, str) and col.startswith('Annual'):
            year = int(col.split('\n')[-1])
            year_columns[col] = year
    wide = wide[['series_id', *year_columns.keys()]]
    long_df = wide.melt(id_vars='series_id', value_vars=year_columns.keys(),
                        var_name='year', value_name='employment')
    long_df['year'] = long_df['year'].map(year_columns)
    long_df['employment'] = pd.to_numeric(long_df['employment'], errors='coerce')
    long_df['naics_code'] = long_df['series_id'].str.extract(r'(\d{4})$')
    long_df = long_df.dropna(subset=['naics_code', 'employment'])
    long_df['naics_code'] = long_df['naics_code'].astype(str)
    return long_df


def add_segment_metadata(df: pd.DataFrame) -> pd.DataFrame:
    lookup = pd.read_csv(SEGMENT_LOOKUP_PATH, dtype={'naics_code': str})[
        ['naics_code', 'segment_id', 'segment_name', 'stage']
    ].drop_duplicates()
    merged = df.merge(lookup, on='naics_code', how='left', indicator=True)
    missing = merged[merged['_merge'] == 'left_only']['naics_code'].unique()
    if len(missing) > 0:
        raise ValueError(f'Missing segment assignment for NAICS codes: {", ".join(sorted(missing))}')
    merged = merged.drop(columns=['_merge'])
    merged['segment_id'] = pd.to_numeric(merged['segment_id'], errors='coerce').astype('Int64')
    merged['segment_label'] = merged['segment_id'].map(SEGMENT_LABELS)
    merged['stage'] = merged['stage'].astype(str)
    return merged


def aggregate_to_segment(df: pd.DataFrame) -> pd.DataFrame:
    seg = (
        df.groupby(['segment_id', 'segment_label', 'year'], as_index=False)
        ['employment'].sum(min_count=1)
        .rename(columns={'employment': 'employment_qcew'})
    )
    return seg


def aggregate_to_stage(df: pd.DataFrame) -> pd.DataFrame:
    stage = (
        df.groupby(['stage', 'year'], as_index=False)
        ['employment'].sum(min_count=1)
        .rename(columns={'employment': 'employment_qcew'})
    )
    return stage


def main() -> None:
    qcew_long = load_qcew()
    qcew_long = add_segment_metadata(qcew_long)

    qcew_long.to_csv(RAW_LONG_OUTPUT, index=False)

    segment_ts = aggregate_to_segment(qcew_long)
    stage_ts = aggregate_to_stage(qcew_long)

    segment_ts.sort_values(['segment_id', 'year']).to_csv(SEGMENT_OUTPUT, index=False)
    stage_ts.sort_values(['stage', 'year']).to_csv(STAGE_OUTPUT, index=False)

    segment_ts.to_csv(SEGMENT_PROCESSED_OUTPUT, index=False)
    stage_ts.to_csv(STAGE_PROCESSED_OUTPUT, index=False)


if __name__ == '__main__':
    main()
