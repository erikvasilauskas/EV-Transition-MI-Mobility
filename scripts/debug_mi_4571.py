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

    pivot_2024 = subset.pivot(index='naics_code', columns='metric_key', values=f'value_{YEARS[0]}').add_prefix(f'{YEARS[0]}_')
    pivot_2030 = subset.pivot(index='naics_code', columns='metric_key', values=f'value_{YEARS[1]}').add_prefix(f'{YEARS[1]}_')
    pivot_pct = subset.pivot(index='naics_code', columns='metric_key', values='pct_change').add_prefix(f'pct_change_{YEARS[0]}_{YEARS[1]}_')
    result = pd.concat([pivot_2024, pivot_2030, pivot_pct], axis=1).reset_index()
    return result


df = load_data()
mi_table = compute_geography_table(df, 'Michigan')
row = mi_table[mi_table['naics_code'] == '4571']
print(row.T)
