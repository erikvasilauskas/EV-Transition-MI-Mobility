from pathlib import Path
text = Path("scripts/occupation_forecasts_from_segment_totals.py").read_text(encoding="utf-8")

# 1. ensure ep_openings_annual_avg kept
def add_openings_keep(txt: str) -> str:
    target = "        \"ep_edu_grouped\",\n    ]"
    replacement = "        \"ep_edu_grouped\",\n        \"ep_openings_annual_avg\",\n    ]"
    if "ep_openings_annual_avg" not in txt:
        txt = txt.replace(target, replacement, 1)
    return txt

text = add_openings_keep(text)

# 2. update build_forecasts signature call in main
text = text.replace(
    "    forecasts = build_forecasts(segment_totals, share_df)\n",
    "    forecasts = build_forecasts(segment_totals, share_df, base_year)\n",
    1,
)

# 3. update function definition
old_def = "def build_forecasts(segment_totals: pd.DataFrame, share_df: pd.DataFrame) -> pd.DataFrame:\n"
if old_def in text:
    text = text.replace(old_def, "def build_forecasts(segment_totals: pd.DataFrame, share_df: pd.DataFrame, base_year: int) -> pd.DataFrame:\n", 1)

# 4. inject base dictionaries and openings calculation
import re
pattern = r"def build_forecasts\(segment_totals: pd.DataFrame, share_df: pd.DataFrame, base_year: int\) -> pd.DataFrame:\n    totals = segment_totals.set_index\(\[\"segment_id\", \"year\", \"methodology\"\]\)  # type: ignore\[arg-type\]\n    records = \[\]\n    methodologies = segment_totals\[\"methodology\"\].unique\(\)\n\n    for _, row in share_df.iterrows\(\):\n        seg_id = row\[\"segment_id\"\]\n        year = row\[\"year\"\]\n        share = row\[\"share\"\]\n        for method in methodologies:\n            key = \(seg_id, year, method\)\n            if key not in totals.index:\n                continue\n            total = totals.loc\[key, \"employment_qcew\"]\n            employment = total * share\n            records.append\({\n                \"segment_id\": seg_id,\n                \"segment_name\": row\[\"segment_name\"\],\n                \"year\": year,\n                \"methodology\": method,\n                \"occcd\": row\[\"occcd\"\],\n                \"soctitle\": row\[\"soctitle\"\],\n                \"employment\": employment,\n                \"share\": share,\n                \"share_2024\": row\[\"share_2024\"\],\n                \"share_2034\": row\[\"share_2034\"\],\n                \"ep_entry_education\": row\[\"ep_entry_education\"\],\n                \"ep_work_experience\": row\[\"ep_work_experience\"\],\n                \"ep_on_the_job_training\": row\[\"ep_on_the_job_training\"\],\n                \"ep_edu_grouped\": row\[\"ep_edu_grouped\"\],\n            }\)\n    return pd.DataFrame\(records\)\n"

replacement = "def build_forecasts(segment_totals: pd.DataFrame, share_df: pd.DataFrame, base_year: int) -> pd.DataFrame:\n    totals = segment_totals.set_index([\"segment_id\", \"year\", \"methodology\"])  # type: ignore[arg-type]\n    records = []\n    methodologies = segment_totals[\"methodology\"].unique()\n\n    base_segment_occup = {}\n    base_occup_totals = {}\n    for _, base_row in share_df.iterrows():\n        seg_id = base_row[\"segment_id\"]\n        share_base = base_row[\"share_2024\"]\n        occ = base_row[\"occcd\"]\n        for method in methodologies:\n            base_key = (seg_id, base_year, method)\n            base_segment_total = totals.loc[base_key, \"employment_qcew\"] if base_key in totals.index else 0.0\n            base_employment = base_segment_total * share_base\n            base_segment_occup[(method, seg_id, occ)] = base_employment\n            occ_key = (method, occ)\n            base_occup_totals[occ_key] = base_occup_totals.get(occ_key, 0.0) + base_employment\n\n    for _, row in share_df.iterrows():\n        seg_id = row[\"segment_id\"]\n        year = row[\"year\"]\n        share = row[\"share\"]\n        occ = row[\"occcd\"]\n        for method in methodologies:\n            key = (seg_id, year, method)\n            if key not in totals.index:\n                continue\n            total = totals.loc[key, \"employment_qcew\"]\n            employment = total * share\n\n            base_emp_segment = base_segment_occup.get((method, seg_id, occ), 0.0)\n            base_occ_total = base_occup_totals.get((method, occ), 0.0)\n            base_openings_segment = 0.0\n            if base_occ_total > 0:\n                base_openings_segment = row.get(\"ep_openings_annual_avg\", 0.0) * (base_emp_segment / base_occ_total)\n            openings = base_openings_segment\n            if base_emp_segment > 0:\n                openings = base_openings_segment * (employment / base_emp_segment)\n\n            records.append({\n                \"segment_id\": seg_id,\n                \"segment_name\": row[\"segment_name\"],\n                \"year\": year,\n                \"methodology\": method,\n                \"occcd\": occ,\n                \"soctitle\": row[\"soctitle\"],\n                \"employment\": employment,\n                \"share\": share,\n                \"share_2024\": row[\"share_2024\"],\n                \"share_2034\": row[\"share_2034\"],\n                \"ep_entry_education\": row[\"ep_entry_education\"],\n                \"ep_work_experience\": row[\"ep_work_experience\"],\n                \"ep_on_the_job_training\": row[\"ep_on_the_job_training\"],\n                \"ep_edu_grouped\": row[\"ep_edu_grouped\"],\n                \"ep_openings_annual_avg\": row.get(\"ep_openings_annual_avg\", 0.0),\n                \"openings\": openings,\n            })\n    return pd.DataFrame(records)\n\n\n
def layout_occupation_insights"

if re.search(pattern, text) is None:
    raise SystemExit("Failed to locate build_forecasts block")

text = re.sub(pattern, replacement, text, count=1)

Path("scripts/occupation_forecasts_from_segment_totals.py").write_text(text, encoding="utf-8")
