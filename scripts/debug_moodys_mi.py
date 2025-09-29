import pandas as pd
from pathlib import Path

RAW_PATH = Path("data/raw/Moody's Supply Chain Employment and Output 1970-2055.xlsx")
YEARS = (2024, 2030)
METRIC_MAP = {
    "Employment": "employment",
    "Wage and salary disbursements": "wages",
    "Gross domestic product": "gdp",
    "Gross product originating": "gdp",
}

def load_data():
    df = pd.read_excel(RAW_PATH)
    df = df.assign(
        metric=df['Description:'].str.split(':').str[0].str.strip(),
        naics_code=df['Mnemonic:'].str.extract(r"(\d{4})").iloc[:, 0].str.zfill(4)
    )
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
    return subset


df = load_data()
mi_subset = compute_geography_table(df, 'Michigan')
missing = mi_subset[mi_subset['pct_change'].isna()]
print('Missing rows:', missing[['naics_code', 'metric_key', f'value_{YEARS[0]}', f'value_{YEARS[1]}']])
print('Unique NAICS count:', mi_subset['naics_code'].nunique())
