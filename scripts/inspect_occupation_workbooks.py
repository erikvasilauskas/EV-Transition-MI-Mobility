import pandas as pd
from pathlib import Path

for year in (2023, 2024):
    path = Path(f"data/raw/occupation_{year}_ep.xlsx")
    xls = pd.ExcelFile(path)
    print(year, xls.sheet_names)
