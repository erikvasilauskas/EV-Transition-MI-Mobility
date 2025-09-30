import nbformat as nbf
from pathlib import Path

notebook_path = Path('notebooks/04_mcda_staffing_analysis.ipynb')

nb = nbf.v4.new_notebook()

cells = []

cells.append(nbf.v4.new_markdown_cell("""# MCDA Staffing Pattern Changes (20212024)

This notebook reviews Michigan Center for Data and Analytics (MCDA) staffing patterns aggregated to the ten supply-chain segments. It highlights employment shifts for major and detailed occupations between 2021 and 2024 and compares educational requirements using employment projections metadata (Table 1.2).
"""))

cells.append(nbf.v4.new_code_cell("""from pathlib import Path
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

sns.set_theme(context='talk', style='whitegrid')
project_root = Path.cwd()
if not (project_root / 'data').exists():
    project_root = project_root.parent
DATA_PROCESSED = project_root / 'data' / 'processed'
DATA_INTERIM = project_root / 'data' / 'interim'
FIG_DIR = project_root / 'reports' / 'figures'
FIG_DIR.mkdir(parents=True, exist_ok=True)
"""))

cells.append(nbf.v4.new_code_cell("""major = pd.read_csv(DATA_PROCESSED / 'mcda_staffing_major_2021_2024.csv')
detailed = pd.read_csv(DATA_PROCESSED / 'mcda_staffing_detailed_2021_2024.csv')
edu_summary = pd.read_csv(DATA_PROCESSED / 'mcda_staffing_education_summary.csv')

major.head()
"""))

cells.append(nbf.v4.new_markdown_cell("""## Aggregated Change by Major Occupation

The table below ranks major occupation families by total employment change across all segments. Values reflect the sum of segment-level changes.
"""))

cells.append(nbf.v4.new_code_cell("""major_totals = (major
                 .groupby(['occcd', 'soctitle'], as_index=False)
                 .agg({
                     'empl_2021': 'sum',
                     'empl_2024': 'sum',
                     'level_change_2021_2024': 'sum'
                 })
                )
major_totals['pct_change_2021_2024'] = ((major_totals['empl_2024'] / major_totals['empl_2021']) - 1) * 100
major_top = major_totals.sort_values('level_change_2021_2024', ascending=False).head(10)
major_bottom = major_totals.sort_values('level_change_2021_2024').head(10)
major_top[['occcd', 'soctitle', 'level_change_2021_2024']]
"""))

cells.append(nbf.v4.new_code_cell("""fig, ax = plt.subplots(figsize=(12, 6))
sns.barplot(data=major_top, x='level_change_2021_2024', y='soctitle', ax=ax, palette='crest')
ax.set_xlabel('Employment Change (2021-2024)')
ax.set_ylabel('Major Occupation')
ax.set_title('Top Employment Gains by Major Occupation (All Segments)')
fig.tight_layout()
fig.savefig(FIG_DIR / 'mcda_major_top_changes.png', dpi=300, bbox_inches='tight')
plt.show()
"""))

cells.append(nbf.v4.new_markdown_cell("""### Largest Declines

The next table lists major occupations with the largest declines in employment.
"""))

cells.append(nbf.v4.new_code_cell("""major_bottom[['occcd', 'soctitle', 'level_change_2021_2024']]
"""))

cells.append(nbf.v4.new_code_cell("""fig, ax = plt.subplots(figsize=(12, 6))
sns.barplot(data=major_bottom.sort_values('level_change_2021_2024'), x='level_change_2021_2024', y='soctitle', ax=ax, palette='flare')
ax.set_xlabel('Employment Change (2021-2024)')
ax.set_ylabel('Major Occupation')
ax.set_title('Largest Employment Declines by Major Occupation (All Segments)')
fig.tight_layout()
fig.savefig(FIG_DIR / 'mcda_major_bottom_changes.png', dpi=300, bbox_inches='tight')
plt.show()
"""))

cells.append(nbf.v4.new_markdown_cell("""## Detailed Occupations: Top Movers

Detailed occupations drive much of the segment-level dynamics. The following chart shows the top 15 detailed occupations by employment growth across all segments.
"""))

cells.append(nbf.v4.new_code_cell("""detailed_totals = (detailed
                    .groupby(['occcd', 'soctitle'], as_index=False)
                    .agg({
                        'empl_2021': 'sum',
                        'empl_2024': 'sum',
                        'level_change_2021_2024': 'sum'
                    })
                   )
detailed_totals['pct_change_2021_2024'] = ((detailed_totals['empl_2024'] / detailed_totals['empl_2021']) - 1) * 100
top15_detailed = detailed_totals.sort_values('level_change_2021_2024', ascending=False).head(15)
fig, ax = plt.subplots(figsize=(12, 8))
sns.barplot(data=top15_detailed, x='level_change_2021_2024', y='soctitle', ax=ax, palette='viridis')
ax.set_xlabel('Employment Change (2021-2024)')
ax.set_ylabel('Detailed Occupation')
ax.set_title('Top Detailed Occupation Gains (All Segments)')
fig.tight_layout()
fig.savefig(FIG_DIR / 'mcda_detailed_top_changes.png', dpi=300, bbox_inches='tight')
plt.show()
"""))

cells.append(nbf.v4.new_markdown_cell("""## Education Composition (Detailed Occupations)

Using the Table 1.2 projections metadata, detailed occupations are mapped to three education groups. The chart below compares the 2021 vs. 2024 mix for each segment.
"""))

cells.append(nbf.v4.new_code_cell("""edu_segments = edu_summary[edu_summary['segment'] != 'All Segments Combined'].copy()
edu_long = edu_segments.melt(id_vars=['segment', 'edu_group'], value_vars=['share_2021', 'share_2024'],
                            var_name='year', value_name='share')
edu_long['year'] = edu_long['year'].str.extract('(\\d{4})').astype('Int64')
edu_long = edu_long.dropna(subset=['year'])
fig, ax = plt.subplots(figsize=(12, 6))
sns.barplot(data=edu_long, x='segment', y='share', hue='edu_group', ax=ax)
ax.set_ylabel('Share of Detailed Employment')
ax.set_xlabel('Segment')
ax.set_title('Detailed Occupation Mix by Education Requirement')
ax.tick_params(axis='x', rotation=45)
for label in ax.get_xticklabels():
    label.set_horizontalalignment('right')
fig.tight_layout()
fig.savefig(FIG_DIR / 'mcda_detailed_education_mix.png', dpi=300, bbox_inches='tight')
plt.show()
"""))

cells.append(nbf.v4.new_markdown_cell("""## Notes

- Processed inputs generated by scripts/process_mcda_staffing.py.
- Figures are exported to eports/figures/ for use in presentations or dashboards.
- Update raw staffing data or employment projections and rerun the processing script before refreshing this notebook.
"""))

nb['cells'] = cells

notebook_path.parent.mkdir(parents=True, exist_ok=True)
nbf.write(nb, notebook_path)
