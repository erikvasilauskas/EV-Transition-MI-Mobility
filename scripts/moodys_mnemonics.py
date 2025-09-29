import pandas as pd
from pathlib import Path


def main():
    path = Path("data/raw/Moody's Supply Chain Employment and Output 1970-2055.xlsx")
    df = pd.read_excel(path)
    df['metric'] = df['Description:'].str.split(':').str[0]
    for metric in sorted(df['metric'].unique()):
        subset = df[df['metric'] == metric].head(5)
        print(metric)
        print(subset[['Mnemonic:', 'Geography:', 'Description:']])
        print('\n')


if __name__ == "__main__":
    main()
