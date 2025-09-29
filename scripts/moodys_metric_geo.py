import pandas as pd
from pathlib import Path


def main():
    path = Path("data/raw/Moody's Supply Chain Employment and Output 1970-2055.xlsx")
    df = pd.read_excel(path)
    df['metric'] = df['Description:'].str.split(':').str[0]
    counts = df.pivot_table(index='metric', columns='Geography:', values='Mnemonic:', aggfunc='count')
    print(counts)


if __name__ == "__main__":
    main()
