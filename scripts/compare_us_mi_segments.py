# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

import pandas as pd

US_LONG_PATH = Path('data/interim/us_staffing_segments_long_2024_2034.csv')
MI_WIDE_PATH = Path('data/interim/mcda_staffing_wide_2021_2024_enriched.csv')
MAJOR_OUTPUT = Path('data/processed/us_mi_segment_comparison_major.csv')
DETAILED_OUTPUT = Path('data/processed/us_mi_segment_comparison_detailed.csv')
FLAGS_OUTPUT = Path('data/processed/us_mi_segment_comparison_flags.csv')

MAJOR_CODES = {'major'}
DETAILED_CODES = {'detailed'}
SUMMARY_SUFFIX = '-0000'

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


def load_us_data() -> pd.DataFrame:
    df = pd.read_csv(US_LONG_PATH)
    df['segment_id'] = pd.to_numeric(df['segment_id'], errors='coerce', downcast='integer')
    df.rename(columns={'segment_name': 'segment_label_us'}, inplace=True)
    df['segment_label_us'] = df['segment_id'].map(SEGMENT_LABELS).combine_first(df['segment_label_us'])
    df['Occupation Code'] = df['Occupation Code'].astype(str).str.strip()
    df['segment_share_2024'] = pd.to_numeric(df['segment_share_2024'], errors='coerce')
    df['segment_share_2034'] = pd.to_numeric(df['segment_share_2034'], errors='coerce')
    df['2024 Employment'] = pd.to_numeric(df['2024 Employment'], errors='coerce')
    df['Projected 2034 Employment'] = pd.to_numeric(df['Projected 2034 Employment'], errors='coerce')
    df['Employment Change, 2024-2034'] = pd.to_numeric(df['Employment Change, 2024-2034'], errors='coerce')
    df['Employment Percent Change, 2024-2034'] = pd.to_numeric(df['Employment Percent Change, 2024-2034'], errors='coerce')
    return df


def load_mi_data() -> pd.DataFrame:
    df = pd.read_csv(MI_WIDE_PATH)
    df.rename(columns={'segment_name': 'segment_label_raw'}, inplace=True)
    df['segment_label_raw'] = df['segment_label_raw'].astype(str).str.strip()
    df['segment_id'] = pd.to_numeric(df['segment_label_raw'].str.extract(r'^(\d+)')[0], errors='coerce', downcast='integer')
    df['segment_label_mi'] = df['segment_id'].map(SEGMENT_LABELS).combine_first(df['segment_label_raw'])
    df['occ_level'] = df['occ_level'].astype(str).str.lower()
    df['occcd'] = df['occcd'].astype(str).str.strip()
    df['pct_seg_major_2024'] = pd.to_numeric(df['pct_seg_major_2024'], errors='coerce')
    df['pct_seg_detailed_2024'] = pd.to_numeric(df['pct_seg_detailed_2024'], errors='coerce')
    return df


def prepare_major_comparison(us_df: pd.DataFrame, mi_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    us_major = us_df[us_df['Occupation Code'].str.endswith(SUMMARY_SUFFIX)].copy()
    us_major = us_major.rename(columns={'Occupation Code': 'occcd'})

    mi_major = mi_df[mi_df['occ_level'].isin(MAJOR_CODES)].copy()

    merged = us_major.merge(
        mi_major,
        on=['segment_id', 'occcd'],
        how='outer',
        suffixes=('_us', '_mi'),
        indicator=True,
    )

    merged['segment_name'] = merged['segment_label_us'].combine_first(merged['segment_label_mi'])
    merged['share_diff_2024'] = merged['segment_share_2024'] - merged['pct_seg_major_2024']
    merged['share_diff_pct_points'] = merged['share_diff_2024'] * 100

    flags = merged[merged['_merge'] != 'both'][['segment_id', 'segment_name', 'occcd', '_merge']].copy()
    flags['issue'] = flags['_merge'].map({
        'left_only': 'missing_in_mi',
        'right_only': 'missing_in_us',
        'both': 'ok'
    })
    flags = flags.drop(columns=['_merge'])

    merged = merged.drop(columns=['_merge'])
    return merged, flags.assign(level='major')


def prepare_detailed_comparison(us_df: pd.DataFrame, mi_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    us_detailed = us_df[~us_df['Occupation Code'].str.endswith(SUMMARY_SUFFIX)].copy()
    us_detailed = us_detailed.rename(columns={'Occupation Code': 'occcd'})

    mi_detailed = mi_df[mi_df['occ_level'].isin(DETAILED_CODES)].copy()

    merged = us_detailed.merge(
        mi_detailed,
        on=['segment_id', 'occcd'],
        how='outer',
        suffixes=('_us', '_mi'),
        indicator=True,
    )

    merged['segment_name'] = merged['segment_label_us'].combine_first(merged['segment_label_mi'])
    merged['share_diff_2024'] = merged['segment_share_2024'] - merged['pct_seg_detailed_2024']
    merged['share_diff_pct_points'] = merged['share_diff_2024'] * 100

    flags = merged[merged['_merge'] != 'both'][['segment_id', 'segment_name', 'occcd', '_merge']].copy()
    flags['issue'] = flags['_merge'].map({
        'left_only': 'missing_in_mi',
        'right_only': 'missing_in_us',
        'both': 'ok'
    })
    flags = flags.drop(columns=['_merge'])

    merged = merged.drop(columns=['_merge'])
    return merged, flags.assign(level='detailed')


def main() -> None:
    us_df = load_us_data()
    mi_df = load_mi_data()

    major_comparison, major_flags = prepare_major_comparison(us_df, mi_df)
    detailed_comparison, detailed_flags = prepare_detailed_comparison(us_df, mi_df)

    major_comparison.to_csv(MAJOR_OUTPUT, index=False)
    detailed_comparison.to_csv(DETAILED_OUTPUT, index=False)

    flags = pd.concat([major_flags, detailed_flags], ignore_index=True)
    if not flags.empty:
        flags.to_csv(FLAGS_OUTPUT, index=False)
    elif FLAGS_OUTPUT.exists():
        FLAGS_OUTPUT.unlink()


if __name__ == '__main__':
    main()
