"""
Quick validation script to test data availability for occupation forecasts.
Run this before create_occupation_forecasts.py to catch data issues early.
"""

import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_RAW = BASE_DIR / "data" / "raw"
DATA_INTERIM = BASE_DIR / "data" / "interim"
DATA_PROCESSED = BASE_DIR / "data" / "processed"

print("=" * 80)
print("OCCUPATION FORECAST DATA VALIDATION")
print("=" * 80)

# Test 1: MCDA data
print("\n[1/6] Checking MCDA data...")
try:
    mcda = pd.read_csv(DATA_INTERIM / "mcda_staffing_long_2021_2024.csv")
    mcda_2024 = mcda[mcda['year'] == 2024]

    # Check for Total rows
    total_rows = len(mcda_2024[mcda_2024['segment'] == 'Total'])
    if total_rows > 0:
        print(f"  ⚠ Found {total_rows} 'Total' rows (will be filtered out)")

    mcda_2024 = mcda_2024[mcda_2024['segment'] != 'Total']
    print(f"  ✓ MCDA 2024: {len(mcda_2024)} records (excluding totals)")

    # Extract segment IDs
    segment_ids = mcda_2024['segment'].str.split('.').str[0].str.strip()
    print(f"    Segments: {sorted(segment_ids.unique())}")
    print(f"    Occupations: {mcda_2024['occcd'].nunique()}")
except Exception as e:
    print(f"  ✗ Error: {e}")

# Test 2: Segment assignments
print("\n[2/6] Checking segment assignments...")
try:
    segments = pd.read_csv(BASE_DIR / "data" / "lookups" / "segment_assignments.csv")
    print(f"  ✓ Segment assignments: {len(segments)} NAICS codes")
    print(f"    Segments: {sorted(segments['segment_id'].unique())}")
except Exception as e:
    print(f"  ✗ Error: {e}")

# Test 3: Attribution files
print("\n[3/6] Checking attribution files...")
try:
    bea = pd.read_csv(DATA_RAW / "auto_attribution_bea.csv")
    print(f"  ✓ BEA attribution: {len(bea)} NAICS codes")
    lightcast = pd.read_csv(DATA_RAW / "auto_attribution_core_auto_lightcast.csv")
    print(f"  ✓ Lightcast attribution: {len(lightcast)} NAICS codes")
except Exception as e:
    print(f"  ✗ Error: {e}")

# Test 4: Segment forecasts
print("\n[4/6] Checking segment forecasts...")
forecast_files = {
    'BEA_Moody': 'mi_qcew_segment_employment_timeseries_bea_extended_moody.csv',
    'BEA_BLS': 'mi_qcew_segment_employment_timeseries_bea_extended_bls.csv',
    'Lightcast_Moody': 'mi_qcew_segment_employment_timeseries_coreauto_extended_moody.csv',
    'Lightcast_BLS': 'mi_qcew_segment_employment_timeseries_coreauto_extended_bls.csv',
}

for key, filename in forecast_files.items():
    try:
        df = pd.read_csv(DATA_PROCESSED / filename)
        df_24_34 = df[(df['year'] >= 2024) & (df['year'] <= 2034)]
        print(f"  ✓ {key}: {len(df_24_34)} records (2024-2034)")
    except Exception as e:
        print(f"  ✗ {key}: {e}")

# Test 5: BLS staffing patterns
print("\n[5/6] Checking BLS staffing patterns...")
try:
    us_staffing_dir = DATA_RAW / "us_staffing_patterns"
    files = list(us_staffing_dir.glob("us_staffing_*.csv"))
    print(f"  ✓ BLS staffing files: {len(files)} NAICS codes")

    # Check a sample file
    sample = pd.read_csv(files[0])
    print(f"    Sample columns: {list(sample.columns[:5])}")
    required_cols = ['Occupation Code', 'Occupation Title', 'Occupation Type',
                     '2024 Percent of Industry', 'Projected 2034 Percent of Industry']
    missing = [c for c in required_cols if c not in sample.columns]
    if missing:
        print(f"    ✗ Missing columns: {missing}")
    else:
        print(f"    ✓ All required columns present")
except Exception as e:
    print(f"  ✗ Error: {e}")

# Test 6: Data alignment check
print("\n[6/6] Checking data alignment...")
try:
    # Check MCDA segments vs lookup segments
    mcda_segs = set(mcda_2024['segment'].str.split('.').str[0].str.strip().astype(int).unique())
    lookup_segs = set(segments['segment_id'].unique())

    if mcda_segs == lookup_segs:
        print(f"  ✓ MCDA and lookup segments match: {sorted(mcda_segs)}")
    else:
        print(f"  ⚠ Segment mismatch:")
        print(f"    MCDA only: {mcda_segs - lookup_segs}")
        print(f"    Lookup only: {lookup_segs - mcda_segs}")

    # Check NAICS coverage
    bea_naics = set(bea['NAICS'].values)
    lightcast_naics = set(lightcast['naics4'].values)
    segment_naics = set(segments['naics_code'].values)

    print(f"\n  NAICS coverage:")
    print(f"    Segments: {len(segment_naics)} codes")
    print(f"    BEA: {len(segment_naics & bea_naics)}/{len(segment_naics)} covered ({len(segment_naics & bea_naics)/len(segment_naics)*100:.0f}%)")
    print(f"    Lightcast: {len(segment_naics & lightcast_naics)}/{len(segment_naics)} covered ({len(segment_naics & lightcast_naics)/len(segment_naics)*100:.0f}%)")

    if segment_naics - bea_naics:
        print(f"    ⚠ Missing in BEA: {sorted(segment_naics - bea_naics)}")
    if segment_naics - lightcast_naics:
        print(f"    ⚠ Missing in Lightcast: {sorted(segment_naics - lightcast_naics)}")

except Exception as e:
    print(f"  ✗ Error: {e}")

print("\n" + "=" * 80)
print("VALIDATION COMPLETE")
print("=" * 80)
print("\nIf all checks passed, you can run create_occupation_forecasts.py")
