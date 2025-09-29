import pandas as pd
from pathlib import Path

RAW_PATH = Path("data/raw/Moody's Supply Chain Employment and Output 1970-2055.xlsx")
LOOKUP_PATH = Path("data/lookups/segment_assignments.csv")
INTERIM_DIR = Path("data/interim")
YEARS = (2024, 2030)
METRIC_MAP = {
    "Employment": "employment",
    "Wage and salary disbursements": "wages",
    "Gross domestic product": "gdp",
    "Gross product originating": "gdp",
}
NAICS_REMAPPINGS = {
    '4571': '4471',
}


def load_data():
    df = pd.read_excel(RAW_PATH)
    df = df.assign(
        metric=df['Description:'].str.split(':').str[0].str.strip(),
        naics_code=df['Mnemonic:'].str.extract(r"(\d{4})").iloc[:, 0].str.zfill(4)
    )
    for year in YEARS:
        ts = pd.Timestamp(year=year, month=12, day=31)
        if ts not in df.columns:
            raise KeyError(f"Missing {year} column in Moody's dataset")
    return df


def compute_geography_table(df, geography):
    subset = df[df['Geography:'] == geography].copy()
    subset['metric_key'] = subset['metric'].map(METRIC_MAP)
    subset = subset[subset['metric_key'].notna()]
    subset[f'value_{YEARS[0]}'] = subset[pd.Timestamp(YEARS[0], 12, 31)]
    subset[f'value_{YEARS[1]}'] = subset[pd.Timestamp(YEARS[1], 12, 31)]
    base = subset[f'value_{YEARS[0]}']
    target = subset[f'value_{YEARS[1]}']
    subset['pct_change'] = (target - base) / base.replace({0: pd.NA}) * 100
    subset.loc[base == 0, 'pct_change'] = pd.NA

    pivot_2024 = subset.pivot(index='naics_code', columns='metric_key', values=f'value_{YEARS[0]}').add_prefix(f'{YEARS[0]}_')
    pivot_2030 = subset.pivot(index='naics_code', columns='metric_key', values=f'value_{YEARS[1]}').add_prefix(f'{YEARS[1]}_')
    pivot_pct = subset.pivot(index='naics_code', columns='metric_key', values='pct_change').add_prefix(f'pct_change_{YEARS[0]}_{YEARS[1]}_')

    result = pd.concat([pivot_2024, pivot_2030, pivot_pct], axis=1).reset_index()
    return result


def apply_remappings(df):
    df = df.copy()
    for target, source in NAICS_REMAPPINGS.items():
        if target not in df['naics_code'].values and source in df['naics_code'].values:
            row = df[df['naics_code'] == source].copy()
            if not row.empty:
                row['naics_code'] = target
                df = pd.concat([df, row], ignore_index=True)
    return df


def rename_columns_for_lookup(mi_df):
    rename_map = {
        f'pct_change_{YEARS[0]}_{YEARS[1]}_employment': 'mi_employment_pct_change_2024_2030',
        f'pct_change_{YEARS[0]}_{YEARS[1]}_wages': 'mi_wage_pct_change_2024_2030',
        f'pct_change_{YEARS[0]}_{YEARS[1]}_gdp': 'mi_gdp_pct_change_2024_2030',
    }
    missing_cols = set(rename_map.keys()) - set(mi_df.columns)
    if missing_cols:
        raise KeyError(f"Expected columns missing from Michigan table: {missing_cols}")
    return mi_df[['naics_code'] + list(rename_map.keys())].rename(columns=rename_map)


def main():
    df = load_data()

    us_table = compute_geography_table(df, 'United States')
    mi_table = compute_geography_table(df, 'Michigan')

    us_table = apply_remappings(us_table)
    mi_table = apply_remappings(mi_table)

    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    us_path = INTERIM_DIR / 'moodys_us_2024_2030.csv'
    mi_path = INTERIM_DIR / 'moodys_michigan_2024_2030.csv'
    us_table.to_csv(us_path, index=False)
    mi_table.to_csv(mi_path, index=False)

    lookup = pd.read_csv(LOOKUP_PATH)
    lookup['naics_code'] = lookup['naics_code'].astype(str).str.zfill(4)

    columns_to_remove = [
        c for c in lookup.columns
        if c.startswith('mi_employment_pct_change_2024_2030')
        or c.startswith('mi_wage_pct_change_2024_2030')
        or c.startswith('mi_gdp_pct_change_2024_2030')
    ]
    if columns_to_remove:
        lookup = lookup.drop(columns=columns_to_remove)

    mi_pct = rename_columns_for_lookup(mi_table)
    merged = lookup.merge(mi_pct, on='naics_code', how='left')

    merged.to_csv(LOOKUP_PATH, index=False)


if __name__ == '__main__':
    main()
