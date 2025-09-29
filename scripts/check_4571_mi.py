import pandas as pd
from pathlib import Path

RAW_PATH = Path("data/raw/Moody's Supply Chain Employment and Output 1970-2055.xlsx")
df = pd.read_excel(RAW_PATH)
df = df.assign(
    metric=df['Description:'].str.split(':').str[0].str.strip(),
    naics_code=df['Mnemonic:'].str.extract(r"(\d{4})").iloc[:, 0].str.zfill(4)
)
mi_subset = df[df['Geography:'] == 'Michigan']
print('4571 present in Michigan subset:', '4571' in mi_subset['naics_code'].tolist())
print(mi_subset[mi_subset['naics_code'] == '4571'][['Mnemonic:', 'Description:', df.columns[-1]]])
