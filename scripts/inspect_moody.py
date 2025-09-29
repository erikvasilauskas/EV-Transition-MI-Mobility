import pandas as pd
from pathlib import Path


def main():
    path = Path("data/raw/Moody's Supply Chain Employment and Output 1970-2055.xlsx")
    df = pd.read_excel(path)
    print('Columns:', df.columns.tolist())
    print(df.head())


if __name__ == "__main__":
    main()
