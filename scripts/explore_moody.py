import pandas as pd
from pathlib import Path


def main():
    path = Path("data/raw/Moody's Supply Chain Employment and Output 1970-2055.xlsx")
    df = pd.read_excel(path)
    print('Unique geographies:', df['Geography:'].unique())
    print('Unique native frequencies:', df['Native Frequency:'].unique())
    print('Descriptions sample:', df['Description:'].head(10).tolist())
    print('Row count:', len(df))


if __name__ == "__main__":
    main()
