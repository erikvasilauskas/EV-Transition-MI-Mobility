# -*- coding: utf-8 -*-
import re
from pathlib import Path
from typing import Dict, Iterable, List

import numpy as np
import pandas as pd

RAW_STAFFING = Path('data/raw/Staffing Patterns for 10 Categories.xlsx')
RAW_EP = Path('data/raw/occupation_2024_ep.xlsx')

INTERIM_WIDE_PATH = Path('data/interim/mcda_staffing_wide_2021_2024.csv')
INTERIM_LONG_PATH = Path('data/interim/mcda_staffing_long_2021_2024.csv')
PROCESSED_MAJOR_PATH = Path('data/processed/mcda_staffing_major_2021_2024.csv')
PROCESSED_DETAILED_PATH = Path('data/processed/mcda_staffing_detailed_2021_2024.csv')
PROCESSED_EDU_SUMMARY_PATH = Path('data/processed/mcda_staffing_education_summary.csv')
PROCESSED_MAJOR_XLSX = Path('data/processed/mcda_staffing_major_2021_2024.xlsx')
PROCESSED_DETAILED_XLSX = Path('data/processed/mcda_staffing_detailed_2021_2024.xlsx')
PROCESSED_LONG_XLSX = Path('data/processed/mcda_staffing_long_2021_2024.xlsx')

YEARS = (2021, 2024)


def sanitize_sheet_name(name: str) -> str:
    """Excel-safe sheet names."""
    cleaned = re.sub(r"[\\[\\]\\*\\?/\\\\]", " ", name)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:31] if len(cleaned) > 31 else cleaned


def classify_occ_level(code: str) -> str:
    if not isinstance(code, str):
        return 'unknown'
    code = code.strip()
    if not code:
        return 'unknown'
    if re.match(r"^\d{2}-?0000$", code):
        return 'major'
    if re.match(r"^\d{2}-\d{2}00(?:\.\d{2})?$", code) or re.match(r"^\d{4}00$", code):
        return 'broad'
    if re.match(r"^\d{2}-\d{4}(?:\.\d{2})?$", code) or re.match(r"^\d{6}$", code):
        return 'detailed'
    return 'unknown'


def load_staffing() -> pd.DataFrame:
    xls = pd.ExcelFile(RAW_STAFFING)
    frames: List[pd.DataFrame] = []
    for sheet in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet)
        if df.empty:
            continue
        df.columns = [str(c).strip().lower().replace(' ', '_') for c in df.columns]
        required = {'occcd', 'estyear', 'roundempl'}
        if not required.issubset(df.columns):
            continue
        subset_cols = ['occcd', 'soctitle', 'estyear', 'roundempl']
        for col in subset_cols:
            if col not in df.columns:
                df[col] = np.nan
        df = df[subset_cols]
        df['segment'] = sheet
        frames.append(df)
    if not frames:
        raise RuntimeError('No staffing sheets loaded')
    combined = pd.concat(frames, ignore_index=True)
    combined['occcd'] = combined['occcd'].astype(str).str.strip()
    combined['soctitle'] = combined['soctitle'].astype(str).str.strip()
    combined['estyear'] = pd.to_numeric(combined['estyear'], errors='coerce').astype('Int64')
    combined['roundempl'] = pd.to_numeric(combined['roundempl'], errors='coerce')
    combined = combined.dropna(subset=['occcd', 'estyear'])
    combined = combined[combined['estyear'].isin(YEARS)]
    combined = combined.replace({'soctitle': {'nan': np.nan}})
    return combined


def pivot_staffing(df: pd.DataFrame) -> pd.DataFrame:
    pivot = (
        df
        .pivot_table(index=['segment', 'occcd', 'soctitle'], columns='estyear', values='roundempl', aggfunc='sum')
        .reset_index()
    )
    rename_map = {year: f'empl_{year}' for year in YEARS}
    pivot = pivot.rename(columns=rename_map)
    for year in YEARS:
        col = f'empl_{year}'
        if col not in pivot:
            pivot[col] = np.nan
    pivot['occ_level'] = pivot['occcd'].apply(classify_occ_level)
    pivot['is_total_all'] = pivot['occcd'].str.replace(r'\D', '', regex=True).eq('000000')
    return pivot


def compute_segment_shares(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for year in YEARS:
        col = f'empl_{year}'
        # Major share
        mask_major = (df['occ_level'] == 'major') & (~df['is_total_all'])
        if mask_major.any():
            totals_major = df.loc[mask_major].groupby('segment')[col].transform('sum')
            df.loc[mask_major, f'pct_seg_major_{year}'] = np.where(
                totals_major > 0,
                df.loc[mask_major, col] / totals_major,
                np.nan
            )
        else:
            df[f'pct_seg_major_{year}'] = np.nan
        # Detailed share
        mask_detailed = df['occ_level'] == 'detailed'
        if mask_detailed.any():
            totals_detailed = df.loc[mask_detailed].groupby('segment')[col].transform('sum')
            df.loc[mask_detailed, f'pct_seg_detailed_{year}'] = np.where(
                totals_detailed > 0,
                df.loc[mask_detailed, col] / totals_detailed,
                np.nan
            )
        else:
            df[f'pct_seg_detailed_{year}'] = np.nan
    df['level_change_2021_2024'] = df['empl_2024'] - df['empl_2021']
    df['pct_change_2021_2024'] = np.where(
        (df['empl_2021'].notna()) & (df['empl_2021'] != 0) & df['empl_2024'].notna(),
        (df['empl_2024'] / df['empl_2021'] - 1) * 100,
        np.nan
    )
    return df


def find_column(columns: Iterable[str], *tokens: str) -> str:
    lower_tokens = [t.lower() for t in tokens]
    for col in columns:
        col_lower = col.lower()
        if all(tok in col_lower for tok in lower_tokens):
            return col
    raise KeyError(f'Unable to locate column with tokens {tokens}')


def load_ep_data() -> pd.DataFrame:
    df = pd.read_excel(RAW_EP, sheet_name='Table 1.2', skiprows=1)
    columns = list(df.columns)
    col_map: Dict[str, str] = {
        find_column(columns, 'matrix', 'title'): 'ep_title',
        find_column(columns, 'matrix', 'code'): 'occcd',
        find_column(columns, 'occupation type'): 'ep_type',
        find_column(columns, 'employment,', '2024'): 'ep_employment_2024',
        find_column(columns, 'employment,', '2034'): 'ep_employment_2034',
        find_column(columns, 'employment change', 'numeric'): 'ep_change_numeric',
        find_column(columns, 'employment change', 'percent'): 'ep_change_percent',
        find_column(columns, 'occupational openings'): 'ep_openings_annual_avg',
        find_column(columns, 'median annual wage'): 'ep_median_annual_wage_2024',
        find_column(columns, 'education needed'): 'ep_entry_education',
        find_column(columns, 'work experience'): 'ep_work_experience',
        find_column(columns, 'on-the-job training'): 'ep_on_the_job_training'
    }
    ep_df = df[list(col_map.keys())].rename(columns=col_map)
    ep_df['occcd'] = ep_df['occcd'].astype(str).str.strip()
    ep_df['ep_entry_education'] = ep_df['ep_entry_education'].astype(str).str.strip()
    ep_df['ep_work_experience'] = ep_df['ep_work_experience'].astype(str).str.strip()
    ep_df['ep_on_the_job_training'] = ep_df['ep_on_the_job_training'].astype(str).str.strip()

    def categorize_education(value: str) -> str:
        if not isinstance(value, str):
            return np.nan
        value = value.strip()
        if value in {
            'No formal educational credential',
            'High school diploma or equivalent'
        }:
            return 'HS or less'
        if value in {
            "Postsecondary nondegree award",
            "Associate's degree",
            'Some college, no degree'
        }:
            return "SC or associate's"
        if value in {
            "Bachelor's degree",
            "Master's degree",
            'Doctoral or professional degree'
        }:
            return 'BA+'
        return np.nan

    ep_df['ep_edu_grouped'] = ep_df['ep_entry_education'].apply(categorize_education)
    return ep_df


def attach_ep(df: pd.DataFrame, ep_df: pd.DataFrame) -> pd.DataFrame:
    merged = df.merge(ep_df, on='occcd', how='left')
    ep_cols = [c for c in merged.columns if c.startswith('ep_')]
    if ep_cols:
        detailed_mask = merged['occ_level'] == 'detailed'
        for col in ep_cols:
            merged.loc[~detailed_mask, col] = np.nan
    return merged


def build_long(df: pd.DataFrame) -> pd.DataFrame:
    share_2021 = np.where(
        df['occ_level'] == 'major',
        df['pct_seg_major_2021'],
        np.where(df['occ_level'] == 'detailed', df['pct_seg_detailed_2021'], np.nan)
    )
    share_2024 = np.where(
        df['occ_level'] == 'major',
        df['pct_seg_major_2024'],
        np.where(df['occ_level'] == 'detailed', df['pct_seg_detailed_2024'], np.nan)
    )
    long_frames = []
    long_frames.append(
        pd.DataFrame(
            {
                'segment': df['segment'],
                'occcd': df['occcd'],
                'soctitle': df['soctitle'],
                'occ_level': df['occ_level'],
                'year': YEARS[0],
                'employment': df['empl_2021'],
                'share_within_level': share_2021,
            }
        )
    )
    long_frames.append(
        pd.DataFrame(
            {
                'segment': df['segment'],
                'occcd': df['occcd'],
                'soctitle': df['soctitle'],
                'occ_level': df['occ_level'],
                'year': YEARS[1],
                'employment': df['empl_2024'],
                'share_within_level': share_2024,
            }
        )
    )
    long_df = pd.concat(long_frames, ignore_index=True)
    ep_cols = [c for c in df.columns if c.startswith('ep_')]
    if ep_cols:
        long_df = long_df.merge(df[['segment', 'occcd'] + ep_cols], on=['segment', 'occcd'], how='left')
    return long_df


def build_education_summary(detailed_df: pd.DataFrame) -> pd.DataFrame:
    edu_df = detailed_df.copy()
    edu_df = edu_df[~edu_df['ep_edu_grouped'].isna()]
    if edu_df.empty:
        return pd.DataFrame()

    grouped = (
        edu_df
        .groupby(['segment', 'ep_edu_grouped'], as_index=False)
        .agg(
            empl_2021=('empl_2021', 'sum'),
            empl_2024=('empl_2024', 'sum'),
            level_change_2021_2024=('level_change_2021_2024', 'sum')
        )
    )
    grouped['total_2021'] = grouped.groupby('segment')['empl_2021'].transform('sum')
    grouped['total_2024'] = grouped.groupby('segment')['empl_2024'].transform('sum')
    grouped['total_change'] = grouped.groupby('segment')['level_change_2021_2024'].transform('sum')
    grouped['pct_change_2021_2024'] = np.where(
        grouped['empl_2021'] > 0,
        (grouped['empl_2024'] / grouped['empl_2021'] - 1) * 100,
        np.nan
    )
    grouped['percent_share_change_21_24'] = np.where(
        grouped['total_change'] != 0,
        grouped['level_change_2021_2024'] / grouped['total_change'],
        np.nan
    )
    grouped['share_2021'] = np.where(
        grouped['total_2021'] > 0,
        grouped['empl_2021'] / grouped['total_2021'],
        np.nan
    )
    grouped['share_2024'] = np.where(
        grouped['total_2024'] > 0,
        grouped['empl_2024'] / grouped['total_2024'],
        np.nan
    )

    overall = grouped.groupby('ep_edu_grouped', as_index=False).agg(
        empl_2021=('empl_2021', 'sum'),
        empl_2024=('empl_2024', 'sum'),
        level_change_2021_2024=('level_change_2021_2024', 'sum')
    )
    overall['segment'] = 'All Segments Combined'
    overall['total_2021'] = overall['empl_2021'].sum()
    overall['total_2024'] = overall['empl_2024'].sum()
    overall['total_change'] = overall['level_change_2021_2024'].sum()
    overall['pct_change_2021_2024'] = np.where(
        overall['empl_2021'] > 0,
        (overall['empl_2024'] / overall['empl_2021'] - 1) * 100,
        np.nan
    )
    overall['percent_share_change_21_24'] = np.where(
        overall['total_change'] != 0,
        overall['level_change_2021_2024'] / overall['total_change'],
        np.nan
    )
    overall['share_2021'] = np.where(
        overall['total_2021'] > 0,
        overall['empl_2021'] / overall['total_2021'],
        np.nan
    )
    overall['share_2024'] = np.where(
        overall['total_2024'] > 0,
        overall['empl_2024'] / overall['total_2024'],
        np.nan
    )

    combined = pd.concat([grouped, overall], ignore_index=True)
    combined = combined.rename(columns={'ep_edu_grouped': 'edu_group'})
    return combined[['segment', 'edu_group', 'empl_2021', 'empl_2024', 'level_change_2021_2024',
                     'pct_change_2021_2024', 'percent_share_change_21_24', 'share_2021', 'share_2024']]


def write_segmented_excel(df: pd.DataFrame, path: Path, sort_cols: List[str]) -> None:
    if df.empty:
        return
    with pd.ExcelWriter(path) as writer:
        for segment, seg_df in df.groupby('segment'):
            sheet_name = sanitize_sheet_name(segment)
            seg_out = seg_df.drop(columns=['segment']).sort_values(sort_cols)
            seg_out.to_excel(writer, sheet_name=sheet_name, index=False)


def write_long_excel(df: pd.DataFrame, path: Path) -> None:
    if df.empty:
        return
    with pd.ExcelWriter(path) as writer:
        df.sort_values(['segment', 'occ_level', 'occcd', 'year']).to_excel(writer, sheet_name='Long', index=False)


def main() -> None:
    staffing = load_staffing()
    wide = pivot_staffing(staffing)
    wide = compute_segment_shares(wide)

    ep_df = load_ep_data()
    wide = attach_ep(wide, ep_df)

    wide.to_csv(INTERIM_WIDE_PATH, index=False)

    long_df = build_long(wide)
    long_df.to_csv(INTERIM_LONG_PATH, index=False)

    major = wide[wide['occ_level'] == 'major'].copy()
    detailed = wide[wide['occ_level'] == 'detailed'].copy()
    major.to_csv(PROCESSED_MAJOR_PATH, index=False)
    detailed.to_csv(PROCESSED_DETAILED_PATH, index=False)

    edu_summary = build_education_summary(detailed)
    if not edu_summary.empty:
        edu_summary.to_csv(PROCESSED_EDU_SUMMARY_PATH, index=False)

    write_segmented_excel(major, PROCESSED_MAJOR_XLSX, sort_cols=['occ_level', 'occcd'])
    write_segmented_excel(detailed, PROCESSED_DETAILED_XLSX, sort_cols=['occ_level', 'empl_2024', 'occcd'])
    write_long_excel(long_df, PROCESSED_LONG_XLSX)


if __name__ == '__main__':
    main()
