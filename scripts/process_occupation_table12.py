# -*- coding: utf-8 -*-
import pandas as pd
from pathlib import Path

RAW_DIR = Path('data/raw')
INTERIM_DIR = Path('data/interim')
PROCESSED_DIR = Path('data/processed')

FILE_TEMPLATE = 'occupation_{year}_ep.xlsx'
SHEET_NAME = 'Table 1.2'

NUMERIC_FIELDS = [
    'employment_base',
    'employment_proj',
    'share_base',
    'share_proj',
    'change_numeric',
    'change_percent',
    'self_employed',
    'openings',
    'median_wage',
]

INVALID_CHARS = {chr(0xFFFD): pd.NA, chr(0x2014): pd.NA, chr(0x2013): pd.NA}

def get_column_mapping(columns: list[str], year: int) -> dict[str, str]:
    def find(*phrases: str) -> str:
        for col in columns:
            if all(phrase in str(col) for phrase in phrases):
                return col
        raise KeyError(f'Could not locate column with tokens {phrases} for year {year}')

    mapping = {
        'title': find('National Employment Matrix title'),
        'code': find('National Employment Matrix code'),
        'type': find('Occupation type'),
        'employment_base': find('Employment,', str(year)),
        'employment_proj': find('Employment,', str(year + 10)),
        'share_base': find('Employment distribution', str(year)),
        'share_proj': find('Employment distribution', str(year + 10)),
        'change_numeric': find('Employment change, numeric'),
        'change_percent': find('Employment change, percent'),
        'self_employed': find('Percent self employed'),
        'openings': find('Occupational openings'),
        'median_wage': find('Median annual wage'),
    }
    return mapping

def load_year(year: int) -> pd.DataFrame:
    path = RAW_DIR / FILE_TEMPLATE.format(year=year)
    read_kwargs = {'sheet_name': SHEET_NAME}
    if year == 2024:
        read_kwargs['skiprows'] = 1
    df = pd.read_excel(path, **read_kwargs)

    mapping = get_column_mapping(list(df.columns), year)
    df = df.rename(columns={source: target for target, source in mapping.items()})

    keep_cols = ['title', 'code', 'type'] + NUMERIC_FIELDS
    df = df[keep_cols]

    df = df[~df['type'].isna()]

    df = df.replace(INVALID_CHARS)
    df['type'] = df['type'].str.strip()
    df['title'] = df['title'].astype(str).str.strip()

    for field in NUMERIC_FIELDS:
        df[field] = pd.to_numeric(df[field], errors='coerce')

    df['base_year'] = year
    df['projection_year'] = year + 10

    return df.reset_index(drop=True)

def build_interim_output(dfs: dict[int, pd.DataFrame]):
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(INTERIM_DIR / 'occupation_table12_clean.xlsx', engine='openpyxl') as writer:
        for year, data in dfs.items():
            data.to_excel(writer, sheet_name=f'table12_{year}', index=False)

    tidy_rows = []
    for year, df in dfs.items():
        tidy = df.assign(year=year)[['year', 'title', 'code', 'type'] + NUMERIC_FIELDS]
        tidy_rows.append(tidy)
    tidy_all = pd.concat(tidy_rows, ignore_index=True)
    tidy_all.to_csv(INTERIM_DIR / 'occupation_table12_tidy.csv', index=False)

def build_processed_output(df_2023: pd.DataFrame, df_2024: pd.DataFrame):
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    merge_keys = ['code', 'type']
    merged = df_2023.merge(
        df_2024,
        on=merge_keys,
        how='outer',
        suffixes=('_2023', '_2024'),
        indicator=True,
    )

    merged['title_2023'] = merged['title_2023'].fillna(merged['title_2024'])
    merged['title_2024'] = merged['title_2024'].fillna(merged['title_2023'])

    for col in NUMERIC_FIELDS:
        merged[f'{col}_delta'] = merged[f'{col}_2024'] - merged[f'{col}_2023']

    merged.sort_values(['type', 'code'], inplace=True)

    with pd.ExcelWriter(PROCESSED_DIR / 'occupation_table12_comparison.xlsx', engine='openpyxl') as writer:
        for occ_type in ['Summary', 'Line item']:
            mask = merged['type'].str.lower() == occ_type.lower()
            subset = merged[mask].copy()
            subset.to_excel(writer, sheet_name=occ_type.replace(' ', '_'), index=False)

    merged.to_csv(PROCESSED_DIR / 'occupation_table12_comparison.csv', index=False)

def main():
    df_2023 = load_year(2023)
    df_2024 = load_year(2024)

    build_interim_output({2023: df_2023, 2024: df_2024})
    build_processed_output(df_2023, df_2024)

if __name__ == '__main__':
    main()
