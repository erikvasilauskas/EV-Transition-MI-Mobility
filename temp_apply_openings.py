from pathlib import Path
import textwrap

path = Path('scripts/occupation_forecasts_from_segment_totals.py')
text = path.read_text(encoding='utf-8')

if 'ep_openings_annual_avg' not in text:
    text = text.replace(
        "        \"ep_edu_grouped\",\n    ]",
        "        \"ep_edu_grouped\",\n        \"ep_openings_annual_avg\",\n    ]",
        1,
    )

old_block = "def build_forecasts(segment_totals: pd.DataFrame, share_df: pd.DataFrame) -> pd.DataFrame:\n    totals = segment_totals.set_index([\"segment_id\", \"year\", \"methodology\"])  # type: ignore[arg-type]\n    records = []\n    methodologies = segment_totals[\"methodology\"].unique()\n\n    for _, row in share_df.iterrows():\n        seg_id = row[\"segment_id\"]\n        year = row[\"year\"]\n        share = row[\"share\"]\n        for method in methodologies:\n            key = (seg_id, year, method)\n            if key not in totals.index:\n                continue\n            total = totals.loc[key, \"employment_qcew\"]\n            employment = total * share\n            records.append({\n                \"segment_id\": seg_id,\n                \"segment_name\": row[\"segment_name\"],\n                \"year\": year,\n                \"methodology\": method,\n                \"occcd\": row[\"occcd\"],\n                \"soctitle\": row[\"soctitle\"],\n                \"employment\": employment,\n                \"share\": share,\n                \"share_2024\": row[\"share_2024\"],\n                \"share_2034\": row[\"share_2034\"],\n                \"ep_entry_education\": row[\"ep_entry_education\"],\n                \"ep_work_experience\": row[\"ep_work_experience\"],\n                \"ep_on_the_job_training\": row[\"ep_on_the_job_training\"],\n                \"ep_edu_grouped\": row[\"ep_edu_grouped\"],\n            })\n    return pd.DataFrame(records)\n"

new_block = textwrap.dedent("""

def build_forecasts(segment_totals: pd.DataFrame, share_df: pd.DataFrame, base_year: int) -> pd.DataFrame:
    totals = segment_totals.set_index(["segment_id", "year", "methodology"])  # type: ignore[arg-type]
    records: list[dict[str, object]] = []
    methodologies = segment_totals["methodology"].unique()

    base_segment_occup: dict[tuple[str, int, str], float] = {}
    base_occup_totals: dict[tuple[str, str], float] = {}
    for _, base_row in share_df.iterrows():
        seg_id = base_row["segment_id"]
        occ = base_row["occcd"]
        share_base = base_row["share_2024"]
        for method in methodologies:
            base_key = (seg_id, base_year, method)
            base_segment_total = totals.loc[base_key, "employment_qcew"] if base_key in totals.index else 0.0
            base_employment = base_segment_total * share_base
            base_segment_occup[(method, seg_id, occ)] = base_employment
            occ_key = (method, occ)
            base_occup_totals[occ_key] = base_occup_totals.get(occ_key, 0.0) + base_employment

    for _, row in share_df.iterrows():
        seg_id = row["segment_id"]
        year = row["year"]
        share = row["share"]
        occ = row["occcd"]
        for method in methodologies:
            key = (seg_id, year, method)
            if key not in totals.index:
                continue
            total = totals.loc[key, "employment_qcew"]
            employment = total * share

            base_emp_segment = base_segment_occup.get((method, seg_id, occ), 0.0)
            base_occ_total = base_occup_totals.get((method, occ), 0.0)
            base_openings_segment = 0.0
            if base_occ_total > 0:
                base_openings_segment = row.get("ep_openings_annual_avg", 0.0) * (base_emp_segment / base_occ_total)
            openings = base_openings_segment
            if base_emp_segment > 0:
                openings = base_openings_segment * (employment / base_emp_segment)

            records.append({
                "segment_id": seg_id,
                "segment_name": row["segment_name"],
                "year": year,
                "methodology": method,
                "occcd": occ,
                "soctitle": row["soctitle"],
                "employment": employment,
                "share": share,
                "share_2024": row["share_2024"],
                "share_2034": row["share_2034"],
                "ep_entry_education": row["ep_entry_education"],
                "ep_work_experience": row["ep_work_experience"],
                "ep_on_the_job_training": row["ep_on_the_job_training"],
                "ep_edu_grouped": row["ep_edu_grouped"],
                "ep_openings_annual_avg": row.get("ep_openings_annual_avg", 0.0),
                "openings": openings,
            })
    return pd.DataFrame(records)
""")

if old_block not in text:
    raise SystemExit('Original build_forecasts block not found')

text = text.replace(old_block, new_block, 1)

text = text.replace(
    "    forecasts = build_forecasts(segment_totals, share_df)\n",
    "    forecasts = build_forecasts(segment_totals, share_df, base_year)\n",
    1,
)

path.write_text(text, encoding='utf-8')
