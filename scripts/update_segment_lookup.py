import pandas as pd
from pathlib import Path

def main():
    seg_path = Path("data/lookups/segment_assignments.csv")
    qcew_path = Path("data/raw/QCEW_MI_2024.csv")
    seg = pd.read_csv(seg_path)
    seg["naics_code"] = seg["naics_code"].astype(str).str.zfill(4)
    qcew = pd.read_csv(qcew_path)
    qcew["naics_code"] = qcew["naics_code"].astype(str).str.zfill(4)
    merged = seg.merge(qcew[["naics_code", "employment_qcew_2024"]], on="naics_code", how="left")
    missing = merged["employment_qcew_2024"].isna()
    if missing.any():
        missing_codes = ", ".join(merged.loc[missing, "naics_code"].tolist())
        raise ValueError(f"Missing QCEW employment for NAICS codes: {missing_codes}")
    merged.to_csv(seg_path, index=False)

if __name__ == "__main__":
    main()
