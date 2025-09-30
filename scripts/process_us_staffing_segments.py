# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

LOOKUP_PATH = Path('data/lookups/segment_assignments.csv')
US_DATA_DIR = Path('data/raw/us_staffing_patterns')
INTERIM_OUTPUT = Path('data/interim/us_staffing_segments_long_2024_2034.csv')
PROCESSED_OUTPUT = Path('data/processed/us_staffing_segments_summary.csv')
PROCESSED_FLAGS = Path('data/processed/us_staffing_segments_flags.csv')
PROCESSED_SOURCES = Path('data/processed/us_staffing_segment_sources.csv')

NUMERIC_COLUMNS = [
    '2024 Employment',
    '2024 Percent of Industry',
    '2024 Percent of Occupation',
    'Projected 2034 Employment',
    'Projected 2034 Percent of Industry',
    'Projected 2034 Percent of Occupation',
    'Employment Change, 2024-2034',
    'Employment Percent Change, 2024-2034',
]

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


def parse_source_code(url: str) -> str:
    if not isinstance(url, str):
        return ''
    token = url.split('queryParams=')[-1]
    token = token.split('&')[0]
    return token.strip()


def load_us_naics_table(naics_code: str) -> pd.DataFrame:
    path = US_DATA_DIR / f'us_staffing_{naics_code}.csv'
    if not path.exists():
        raise FileNotFoundError(f'Missing US staffing file for NAICS {naics_code}')
    df = pd.read_csv(path)
    df['naics_code'] = df['naics_code'].astype(str).str.strip()
    df['source_code'] = df['source_url'].apply(parse_source_code)
    df['Occupation Code'] = df['Occupation Code'].astype(str).str.strip()
    df['Occupation Title'] = df['Occupation Title'].astype(str).str.strip()
    df['Occupation Type'] = df['Occupation Type'].astype(str).str.strip()
    df['Display Level'] = pd.to_numeric(df['Display Level'], errors='coerce')
    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    return df


def build_segment_rollup() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    lookup = pd.read_csv(LOOKUP_PATH, dtype={'naics_code': str})
    segment_ids = sorted(lookup['segment_id'].dropna().unique())

    records = []
    source_records = []

    for seg_id in segment_ids:
        seg_naics = (
            lookup.loc[lookup['segment_id'] == seg_id, 'naics_code']
            .astype(str)
            .str.strip()
            .tolist()
        )
        stage = lookup.loc[lookup['segment_id'] == seg_id, 'stage'].iloc[0]
        seg_label = SEGMENT_LABELS.get(seg_id, f'Segment {seg_id}')
        seen_sources: Dict[str, List[str]] = {}
        dataframes = []

        for naics in seg_naics:
            try:
                df = load_us_naics_table(naics)
            except FileNotFoundError:
                source_records.append({
                    'segment_id': seg_id,
                    'segment_name': seg_label,
                    'naics_code': naics,
                    'source_code': '',
                    'source_url': '',
                    'used_in_segment': False,
                    'reason': 'missing_us_data',
                })
                continue
            source_code = df['source_code'].iloc[0]
            source_url = df['source_url'].iloc[0]
            used = False
            reason = ''

            if source_code in seen_sources:
                seen_sources[source_code].append(naics)
                reason = 'duplicate_source_within_segment'
            else:
                seen_sources[source_code] = [naics]
                dataframes.append(df)
                used = True

            source_records.append({
                'segment_id': seg_id,
                'segment_name': seg_label,
                'naics_code': naics,
                'source_code': source_code,
                'source_url': source_url,
                'used_in_segment': used,
                'reason': reason,
            })

        if not dataframes:
            continue

        combined = pd.concat(dataframes, ignore_index=True)
        agg = (
            combined
            .groupby(['Occupation Code', 'Occupation Title', 'Occupation Type', 'Display Level'], as_index=False)[NUMERIC_COLUMNS]
            .sum(min_count=1)
        )
        total_row = agg.loc[agg['Occupation Code'] == '00-0000', '2024 Employment']
        total_2024 = total_row.iloc[0] if not total_row.empty else agg['2024 Employment'].sum()
        total_row_2034 = agg.loc[agg['Occupation Code'] == '00-0000', 'Projected 2034 Employment']
        total_2034 = total_row_2034.iloc[0] if not total_row_2034.empty else agg['Projected 2034 Employment'].sum()

        agg['segment_share_2024'] = np.where(
            total_2024 > 0,
            agg['2024 Employment'] / total_2024,
            np.nan,
        )
        agg['segment_share_2034'] = np.where(
            total_2034 > 0,
            agg['Projected 2034 Employment'] / total_2034,
            np.nan,
        )

        agg.insert(0, 'segment_id', seg_id)
        agg.insert(1, 'segment_name', seg_label)
        agg.insert(2, 'stage', stage)
        records.append(agg)

    combined_segments = pd.concat(records, ignore_index=True)
    source_details = pd.DataFrame(source_records)

    flags = []
    source_counts = source_details[source_details['used_in_segment']].groupby('source_code')['segment_id'].nunique()
    for source_code, count in source_counts.items():
        if count > 1:
            affected = source_details[source_details['source_code'] == source_code]['segment_id'].unique().tolist()
            flags.append({
                'source_code': source_code,
                'issue': 'shared_across_segments',
                'segments': ','.join(str(x) for x in sorted(affected)),
            })
    duplicates = source_details[source_details['reason'] == 'duplicate_source_within_segment']
    for _, row in duplicates.iterrows():
        flags.append({
            'source_code': row['source_code'],
            'issue': 'duplicate_within_segment',
            'segments': str(row['segment_id']),
        })
    flags_df = pd.DataFrame(flags).drop_duplicates()

    return combined_segments, source_details, flags_df


def main() -> None:
    combined_segments, source_details, flags_df = build_segment_rollup()
    combined_segments.to_csv(INTERIM_OUTPUT, index=False)

    summary_cols = [
        'segment_id', 'segment_name', 'stage',
        'Occupation Code', 'Occupation Title', 'Occupation Type', 'Display Level',
        '2024 Employment', 'Projected 2034 Employment',
        'Employment Change, 2024-2034', 'Employment Percent Change, 2024-2034',
        'segment_share_2024', 'segment_share_2034'
    ]
    combined_segments[summary_cols].to_csv(PROCESSED_OUTPUT, index=False)
    source_details.to_csv(PROCESSED_SOURCES, index=False)
    if not flags_df.empty:
        flags_df.to_csv(PROCESSED_FLAGS, index=False)
    elif PROCESSED_FLAGS.exists():
        PROCESSED_FLAGS.unlink()


if __name__ == '__main__':
    main()
