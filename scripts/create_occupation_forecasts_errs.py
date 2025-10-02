"""
Create occupation-level employment forecasts for Michigan automotive segments (2024-2034).

This script generates occupation-level projections by:
1. Adjusting MCDA 2024 staffing patterns by core-auto attribution (BEA and Lightcast)
2. Applying segment employment growth rates (Moody's and BLS-derived)
3. Accounting for occupational shifts using BLS 2024-2034 industry×occupation projections

Outputs:
- Occupation-level employment by segment, year, methodology, and attribution
- Special focus on 2030 projections
- Separate files for BEA vs. Lightcast attribution approaches
"""

import pandas as pd
import numpy as np
from pathlib import Path

# Define paths
BASE_DIR = Path(__file__).parent.parent
DATA_RAW = BASE_DIR / "data" / "raw"
DATA_INTERIM = BASE_DIR / "data" / "interim"
DATA_PROCESSED = BASE_DIR / "data" / "processed"

print("=" * 80)
print("OCCUPATION-LEVEL FORECAST GENERATION")
print("=" * 80)

# ============================================================================
# STEP 1: Load core datasets
# ============================================================================
print("\n[1/6] Loading core datasets...")

# Load MCDA 2024 staffing patterns
mcda = pd.read_csv(DATA_INTERIM / "mcda_staffing_long_2021_2024.csv")
mcda_2024 = mcda[mcda['year'] == 2024].copy()

# Filter out "Total" rows (cross-segment aggregates)
mcda_2024 = mcda_2024[mcda_2024['segment'] != 'Total'].copy()

# Filter to detailed occupations only (avoid double-counting from major/broad summaries)
# Occupation hierarchy: 00-0000 (grand total) > XX-0000 (major) > broad > detailed (leaf level)
mcda_2024 = mcda_2024[mcda_2024['occ_level'] == 'detailed'].copy()
print(f"  - Loaded MCDA 2024 staffing: {len(mcda_2024)} detailed occupation-segment records")

# Load segment assignments to get NAICS mapping
segments = pd.read_csv(BASE_DIR / "data" / "lookups" / "segment_assignments.csv")
print(f"  - Loaded segment assignments: {len(segments)} NAICS codes")

# Load attribution shares
bea_attr = pd.read_csv(DATA_RAW / "auto_attribution_bea.csv")
bea_attr = bea_attr.rename(columns={'NAICS': 'naics_code', 'bea_share_to_set': 'auto_share'})
print(f"  - Loaded BEA attribution: {len(bea_attr)} NAICS codes")

lightcast_attr = pd.read_csv(DATA_RAW / "auto_attribution_core_auto_lightcast.csv")
lightcast_attr = lightcast_attr.rename(columns={'naics4': 'naics_code', 'share_to_set': 'auto_share'})
print(f"  - Loaded Lightcast attribution: {len(lightcast_attr)} NAICS codes")

# Load segment employment forecasts (all methodologies)
forecast_files = {
    'BEA_Moody': 'mi_qcew_segment_employment_timeseries_bea_extended_moody.csv',
    'BEA_BLS': 'mi_qcew_segment_employment_timeseries_bea_extended_bls.csv',
    'Lightcast_Moody': 'mi_qcew_segment_employment_timeseries_coreauto_extended_moody.csv',
    'Lightcast_BLS': 'mi_qcew_segment_employment_timeseries_coreauto_extended_bls.csv',
}

forecasts = {}
for key, filename in forecast_files.items():
    df = pd.read_csv(DATA_PROCESSED / filename)
    # Filter to projection years only (2024-2034)
    df = df[(df['year'] >= 2024) & (df['year'] <= 2034)]
    forecasts[key] = df
    print(f"  - Loaded {key} forecast: {len(df)} segment-year records")

# ============================================================================
# STEP 2: Load BLS occupational shift data (2024 vs 2034 shares)
# ============================================================================
print("\n[2/6] Loading BLS occupational shift data...")

# Read all BLS us_staffing files and compile occupation shares
bls_shifts = []
us_staffing_dir = DATA_RAW / "us_staffing_patterns"

for naics_file in us_staffing_dir.glob("us_staffing_*.csv"):
    naics_code = int(naics_file.stem.split('_')[-1])

    # Check if this NAICS is in our segment assignments
    if naics_code not in segments['naics_code'].values:
        continue

    df = pd.read_csv(naics_file)

    # Get segment for this NAICS
    segment_info = segments[segments['naics_code'] == naics_code].iloc[0]
    segment_id = segment_info['segment_id']
    segment_name = segment_info['segment_name']

    # Keep only line items (detailed occupations)
    df = df[df['Occupation Type'] == 'Line Item'].copy()

    # Extract relevant columns
    df['naics_code'] = naics_code
    df['segment_id'] = segment_id
    df['segment_name'] = segment_name
    df['occupation_code'] = df['Occupation Code']
    df['occupation_title'] = df['Occupation Title']
    df['share_2024'] = df['2024 Percent of Industry'] / 100  # Convert to proportion
    df['share_2034'] = df['Projected 2034 Percent of Industry'] / 100

    bls_shifts.append(df[['naics_code', 'segment_id', 'segment_name',
                           'occupation_code', 'occupation_title',
                           'share_2024', 'share_2034']])

bls_shifts_df = pd.concat(bls_shifts, ignore_index=True)

# Aggregate to segment level (weighted by QCEW employment)
# Merge with segment assignments to get employment weights
bls_shifts_df = bls_shifts_df.merge(
    segments[['naics_code', 'employment_qcew_2024']],
    on='naics_code'
)

# Weight shares by NAICS employment within segment
segment_occupation_shares = []
for segment_id in bls_shifts_df['segment_id'].unique():
    seg_data = bls_shifts_df[bls_shifts_df['segment_id'] == segment_id]

    # Get total segment employment
    total_emp = seg_data['employment_qcew_2024'].sum()

    # Group by occupation and compute weighted average shares
    for occ_code in seg_data['occupation_code'].unique():
        occ_data = seg_data[seg_data['occupation_code'] == occ_code]

        # Weighted average of shares across NAICS codes in this segment
        share_2024_weighted = (occ_data['share_2024'] * occ_data['employment_qcew_2024']).sum() / total_emp
        share_2034_weighted = (occ_data['share_2034'] * occ_data['employment_qcew_2024']).sum() / total_emp

        segment_occupation_shares.append({
            'segment_id': segment_id,
            'segment_name': seg_data['segment_name'].iloc[0],
            'occupation_code': occ_code,
            'occupation_title': occ_data['occupation_title'].iloc[0],
            'bls_share_2024': share_2024_weighted,
            'bls_share_2034': share_2034_weighted
        })

bls_segment_shifts = pd.DataFrame(segment_occupation_shares)
print(f"  - Compiled BLS shifts: {len(bls_segment_shifts)} segment-occupation pairs")

# ============================================================================
# STEP 3: Adjust MCDA 2024 staffing by auto attribution
# ============================================================================
print("\n[3/6] Adjusting MCDA staffing patterns by auto attribution...")

# Function to compute segment-level weighted auto share
def get_segment_auto_share(segment_id, attribution_df):
    """Get employment-weighted auto share for a segment."""
    seg_naics = segments[segments['segment_id'] == segment_id]['naics_code'].values

    # Merge segment NAICS with attribution
    seg_attr = segments[segments['segment_id'] == segment_id][['naics_code', 'employment_qcew_2024']]
    seg_attr = seg_attr.merge(attribution_df[['naics_code', 'auto_share']], on='naics_code', how='left')

    # Fill missing auto shares with 0 (assume non-auto)
    seg_attr['auto_share'] = seg_attr['auto_share'].fillna(0)

    # Weighted average
    total_emp = seg_attr['employment_qcew_2024'].sum()
    weighted_share = (seg_attr['auto_share'] * seg_attr['employment_qcew_2024']).sum() / total_emp

    return weighted_share

# Extract segment ID from segment column first (format: "1. Materials & Processing")
mcda_2024['segment_id'] = mcda_2024['segment'].str.split('.').str[0].str.strip().astype(int)

# Compute auto shares for each segment
segment_auto_shares = []
for segment_id in sorted(mcda_2024['segment_id'].unique()):
    bea_share = get_segment_auto_share(segment_id, bea_attr)
    lightcast_share = get_segment_auto_share(segment_id, lightcast_attr)

    segment_auto_shares.append({
        'segment_id': segment_id,
        'bea_auto_share': bea_share,
        'lightcast_auto_share': lightcast_share
    })

auto_shares_df = pd.DataFrame(segment_auto_shares)
print(f"  - Computed auto shares for {len(auto_shares_df)} segments")

# Merge auto shares with MCDA data
mcda_adjusted = mcda_2024.merge(auto_shares_df, on='segment_id')

# Adjust employment by auto share
mcda_adjusted['employment_bea'] = mcda_adjusted['employment'] * mcda_adjusted['bea_auto_share']
mcda_adjusted['employment_lightcast'] = mcda_adjusted['employment'] * mcda_adjusted['lightcast_auto_share']

print(f"  - BEA-adjusted employment: {mcda_adjusted['employment_bea'].sum():,.0f}")
print(f"  - Lightcast-adjusted employment: {mcda_adjusted['employment_lightcast'].sum():,.0f}")
print(f"  - Original MCDA employment: {mcda_adjusted['employment'].sum():,.0f}")

# ============================================================================
# STEP 4: Generate occupation forecasts by applying growth rates
# ============================================================================
print("\n[4/6] Generating occupation forecasts (2024-2034)...")

all_occupation_forecasts = []

# Process each methodology × attribution combination
methodology_combinations = [
    ('BEA_Moody', 'bea', 'Moody'),
    ('BEA_BLS', 'bea', 'BLS'),
    ('Lightcast_Moody', 'lightcast', 'Moody'),
    ('Lightcast_BLS', 'lightcast', 'BLS'),
]

for forecast_key, attribution, growth_source in methodology_combinations:
    print(f"\n  Processing: {forecast_key}")

    forecast_df = forecasts[forecast_key]
    emp_col = f'employment_{attribution}'

    # For each segment-occupation in MCDA
    for idx, row in mcda_adjusted.iterrows():
        segment_id = row['segment_id']
        segment_name = row['segment']
        occ_code = row['occcd']
        occ_title = row['soctitle']
        base_emp_2024 = row[emp_col]

        # Get segment employment forecast
        seg_forecast = forecast_df[forecast_df['segment_id'] == segment_id].copy()
        seg_forecast = seg_forecast.sort_values('year')

        # Get BLS occupational shift for this segment-occupation
        bls_shift = bls_segment_shifts[
            (bls_segment_shifts['segment_id'] == segment_id) &
            (bls_segment_shifts['occupation_code'] == occ_code)
        ]

        if len(bls_shift) == 0:
            # No BLS data for this occupation - use segment growth only
            bls_share_2024 = None
            bls_share_2034 = None
        else:
            bls_share_2024 = bls_shift.iloc[0]['bls_share_2024']
            bls_share_2034 = bls_shift.iloc[0]['bls_share_2034']

        # Generate forecast for each year
        for year in range(2024, 2035):
            year_forecast = seg_forecast[seg_forecast['year'] == year]

            if len(year_forecast) == 0:
                continue

            segment_emp = year_forecast.iloc[0]['employment_qcew']

            # Method: Apply both segment growth AND occupational shift
            if bls_share_2024 is not None and bls_share_2024 > 0:
                # Interpolate BLS share for this year
                if year == 2024:
                    bls_share_year = bls_share_2024
                elif year == 2034:
                    bls_share_year = bls_share_2034
                else:
                    # Linear interpolation
                    years_elapsed = year - 2024
                    total_years = 2034 - 2024
                    bls_share_year = bls_share_2024 + (bls_share_2034 - bls_share_2024) * (years_elapsed / total_years)

                # Occupation employment = segment employment × occupation share
                occ_emp = segment_emp * bls_share_year
            else:
                # Fallback: maintain original share from MCDA
                # Get 2024 segment employment
                seg_2024 = seg_forecast[seg_forecast['year'] == 2024]
                if len(seg_2024) > 0:
                    segment_emp_2024 = seg_2024.iloc[0]['employment_qcew']
                    original_share = base_emp_2024 / segment_emp_2024 if segment_emp_2024 > 0 else 0
                    occ_emp = segment_emp * original_share
                else:
                    occ_emp = 0

            all_occupation_forecasts.append({
                'segment_id': segment_id,
                'segment_name': segment_name,
                'occupation_code': occ_code,
                'occupation_title': occ_title,
                'year': year,
                'employment': occ_emp,
                'attribution': attribution,
                'growth_source': growth_source,
                'methodology': f"{attribution}_{growth_source}",
                'has_bls_shift': bls_share_2024 is not None
            })

    print(f"    - Generated {len([f for f in all_occupation_forecasts if f['methodology'] == f'{attribution}_{growth_source}'])} occupation-year forecasts")

occupation_forecasts_df = pd.DataFrame(all_occupation_forecasts)
print(f"\n  Total occupation forecasts: {len(occupation_forecasts_df)}")

# ============================================================================
# STEP 5: Save outputs
# ============================================================================
print("\n[5/6] Saving outputs...")

# Save comprehensive forecast file
output_file = DATA_PROCESSED / "mi_occupation_employment_forecasts_2024_2034.csv"
occupation_forecasts_df.to_csv(output_file, index=False)
print(f"  - Saved: {output_file}")

# Save 2030 snapshot
forecast_2030 = occupation_forecasts_df[occupation_forecasts_df['year'] == 2030].copy()
output_file_2030 = DATA_PROCESSED / "mi_occupation_employment_forecast_2030.csv"
forecast_2030.to_csv(output_file_2030, index=False)
print(f"  - Saved 2030 snapshot: {output_file_2030}")

# Save separate files by attribution approach
for attribution in ['bea', 'lightcast']:
    attr_forecasts = occupation_forecasts_df[occupation_forecasts_df['attribution'] == attribution]
    output_file_attr = DATA_PROCESSED / f"mi_occupation_employment_forecasts_{attribution}_2024_2034.csv"
    attr_forecasts.to_csv(output_file_attr, index=False)
    print(f"  - Saved {attribution.upper()} forecasts: {output_file_attr}")

# ============================================================================
# STEP 6: Generate summary statistics
# ============================================================================
print("\n[6/6] Summary statistics...")

# 2030 employment by segment and methodology
summary_2030 = forecast_2030.groupby(['segment_id', 'segment_name', 'methodology'])['employment'].sum().reset_index()
summary_2030 = summary_2030.pivot(index=['segment_id', 'segment_name'],
                                   columns='methodology',
                                   values='employment').reset_index()

output_summary = DATA_PROCESSED / "mi_occupation_forecast_2030_segment_summary.csv"
summary_2030.to_csv(output_summary, index=False)
print(f"  - Saved 2030 segment summary: {output_summary}")

# Top occupations by 2030 employment (across all methodologies)
top_occupations = forecast_2030.groupby(['occupation_code', 'occupation_title'])['employment'].mean().reset_index()
top_occupations = top_occupations.sort_values('employment', ascending=False).head(20)
print(f"\nTop 20 occupations by 2030 employment (avg across methodologies):")
for idx, row in top_occupations.iterrows():
    print(f"  {row['occupation_code']} - {row['occupation_title']}: {row['employment']:,.0f}")

# Segment totals for 2030
segment_totals_2030 = forecast_2030.groupby(['segment_id', 'segment_name'])['employment'].mean().reset_index()
segment_totals_2030 = segment_totals_2030.sort_values('employment', ascending=False)
print(f"\n2030 Employment by Segment (avg across methodologies):")
for idx, row in segment_totals_2030.iterrows():
    print(f"  Segment {row['segment_id']}: {row['employment']:,.0f}")

# VALIDATION: Check that occupation totals match segment totals
print(f"\n=== VALIDATION: Occupation totals vs. Segment totals ===")
for methodology in ['bea_Moody', 'bea_BLS', 'lightcast_Moody', 'lightcast_BLS']:
    # Get occupation-aggregated totals
    occ_totals_2030 = forecast_2030[forecast_2030['methodology'] == methodology].groupby('segment_id')['employment'].sum()

    # Get original segment forecast totals for 2030
    if 'bea' in methodology:
        if 'Moody' in methodology:
            seg_forecast_file = 'mi_qcew_segment_employment_timeseries_bea_extended_moody.csv'
        else:
            seg_forecast_file = 'mi_qcew_segment_employment_timeseries_bea_extended_bls.csv'
    else:
        if 'Moody' in methodology:
            seg_forecast_file = 'mi_qcew_segment_employment_timeseries_coreauto_extended_moody.csv'
        else:
            seg_forecast_file = 'mi_qcew_segment_employment_timeseries_coreauto_extended_bls.csv'

    seg_forecast = pd.read_csv(DATA_PROCESSED / seg_forecast_file)
    seg_forecast_2030 = seg_forecast[seg_forecast['year'] == 2030]

    # Compare
    max_diff_pct = 0
    for seg_id in occ_totals_2030.index:
        occ_total = occ_totals_2030[seg_id]
        seg_total = seg_forecast_2030[seg_forecast_2030['segment_id'] == seg_id]['employment_qcew'].values[0]
        diff_pct = abs(occ_total - seg_total) / seg_total * 100
        max_diff_pct = max(max_diff_pct, diff_pct)

    print(f"  {methodology}: Max difference = {max_diff_pct:.2f}%")

if max_diff_pct < 5:
    print("  ✓ PASS: Occupation forecasts align with segment totals (<5% difference)")
else:
    print(f"  ⚠ WARNING: Some segments show >{max_diff_pct:.1f}% difference")
    print("    This may indicate missing occupations or share calculation issues")

print("\n" + "=" * 80)
print("OCCUPATION FORECAST GENERATION COMPLETE")
print("=" * 80)
print(f"\nKey outputs:")
print(f"  - {len(occupation_forecasts_df)} total occupation-year-methodology forecasts")
print(f"  - {len(forecast_2030)} occupation forecasts for 2030")
print(f"  - {len(occupation_forecasts_df['occupation_code'].unique())} unique occupations")
print(f"  - {len(occupation_forecasts_df['segment_id'].unique())} segments")
print(f"  - 4 methodology combinations (BEA/Lightcast × Moody/BLS)")
print(f"  - Years: 2024-2034")
