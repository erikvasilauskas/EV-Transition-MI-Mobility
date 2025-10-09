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

old = "                \\\"ep_on_the_job_training\\\": training,\\n                \\\"ep_edu_grouped\\\": edu,\\n            })"
new = "                \"ep_on_the_job_training\": training,\n                \"ep_edu_grouped\": edu,\n                \"ep_openings_annual_avg\": row.get(\"ep_openings_annual_avg\", 0.0),\n            })"
text = text.replace(old, new, 1)

text = text.replace(
    "    aggregated = forecasts.groupby(segment_meta_cols, as_index=False)[\\\"employment\\\"].sum()\n",
    "    aggregated = forecasts.groupby(segment_meta_cols, as_index=False)[\"employment\", \"openings\"].sum()\n",
    1,
)

text = text.replace(
    "    aggregated = aggregated[[\\n        \\\"segment_id\\\",\\n        \\\"segment_name\\\",\\n        \\\"year\\\",\\n        \\\"methodology\\\",\\n        \\\"occcd\\\",\\n        \\\"soctitle\\\",\\n        \\\"employment\\\",\\n        \\\"share\\\",\\n        \\\"share_2024\\\",\\n        \\\"share_2034\\\",\\n        \\\"ep_entry_education\\\",\\n        \\\"ep_work_experience\\\",\\n        \\\"ep_on_the_job_training\\\",\\n        \\\"ep_edu_grouped\\\",\\n    ]]\n",
    "    aggregated = aggregated[[\n        \"segment_id\",\n        \"segment_name\",\n        \"year\",\n        \"methodology\",\n        \"occcd\",\n        \"soctitle\",\n        \"employment\",\n        \"openings\",\n        \"share\",\n        \"share_2024\",\n        \"share_2034\",\n        \"ep_entry_education\",\n        \"ep_work_experience\",\n        \"ep_on_the_job_training\",\n        \"ep_edu_grouped\",\n        \"ep_openings_annual_avg\",\n    ]]\n",
    1,
)

path.write_text(text, encoding='utf-8')
