"""Convert QCEW monthly Excel extract into a tidy CSV for the SAM dashboard."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

RAW_FILE = Path("data/raw/QCEW-AutoEmployment-with-1Q-2025_38_Naics_and_all_industries.xlsx")
OUTPUT_FILE = Path("data/raw/qcew_auto_employment_monthly_clean.csv")

META_COLS = [
    "stage",
    "segment",
    "ice_flag",
    "ev_flag",
    "naics_code",
    "naics_title",
]


def build_column_labels(raw: pd.DataFrame) -> list[str | None]:
    """Return list of column labels combining year/month headers."""
    meta_len = len(META_COLS)
    years = raw.iloc[0, meta_len:]
    months = raw.iloc[1, meta_len:]
    labels: list[str | None] = META_COLS.copy()
    for year, month in zip(years, months):
        if pd.isna(year) or pd.isna(month):
            labels.append(None)
            continue
        try:
            ts = pd.to_datetime(f"{int(year)}-{month}-01")
        except (TypeError, ValueError):
            ts = pd.to_datetime({"year": int(year), "month": int(month), "day": 1})
        labels.append(ts.strftime("%Y-%m"))
    return labels


def classify_row(stage: str, naics_code: str, naics_title: str) -> str:
    title = (naics_title or "").strip().lower()
    code = (naics_code or "").strip()
    if title.startswith("total, all industries"):
        return "all_industries_total"
    if code.isdigit() and len(code) in {4, 5}:
        return "naics_detail"
    return "other"


def clean_text(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip()


def main() -> None:
    raw = pd.read_excel(RAW_FILE, header=None)
    column_labels = build_column_labels(raw)
    keep_indices = [idx for idx, label in enumerate(column_labels) if label is not None]
    raw = raw.iloc[:, keep_indices]
    column_labels = [column_labels[idx] for idx in keep_indices]
    raw.columns = column_labels

    data = raw.iloc[3:].copy()
    data = data.dropna(how="all")
    for col in META_COLS:
        data[col] = clean_text(data[col])

    stage_placeholder = data["stage"].eq("") & data["naics_title"].isin(
        ["Upstream", "Downstream", "OEM", "ICE", "EV", "Total"]
    )
    data.loc[stage_placeholder, "stage"] = data.loc[stage_placeholder, "naics_title"]

    data["row_type"] = data.apply(
        lambda row: classify_row(row["stage"], row["naics_code"], row["naics_title"]), axis=1
    )

    data = data[data["row_type"].isin({"naics_detail", "all_industries_total"})]

    value_cols = [c for c in data.columns if c not in (*META_COLS, "row_type")]
    long_df = data.melt(
        id_vars=META_COLS + ["row_type"],
        value_vars=value_cols,
        var_name="period",
        value_name="employment",
    )
    long_df = long_df.dropna(subset=["employment"], how="all")
    long_df["period"] = pd.to_datetime(long_df["period"], format="%Y-%m")
    long_df.sort_values(["naics_code", "period"], inplace=True)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    long_df.to_csv(OUTPUT_FILE, index=False)
    print(f"Wrote tidy QCEW file to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
