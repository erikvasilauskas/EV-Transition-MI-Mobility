from pathlib import Path
import re
import numpy as np
import pandas as pd

path = Path('dashboards/occupation_forecast_dashboard.py')
text = path.read_text(encoding='utf-8')

pattern = (
    r"def layout_overview\(df: pd.DataFrame, selected_methods: List\[str\]\) -> None:\n"
    r"    st.subheader\(\"Key Highlights\"\)(?:.|\n)*?"
    r"st.caption\(\"Source: data/processed/mi_occ_segment_totals_2024_2034.csv\"\)\n\n"
)

new_block = '''def layout_overview(df: pd.DataFrame, selected_methods: List[str]) -> None:\n    st.subheader("Key Highlights")\n    latest_year = df["year"].max()\n    base_year = df["year"].min()\n\n    method_metrics = []\n    for method in selected_methods:\n        method_df = df[df["methodology"] == method]\n        base_total = method_df[method_df["year"] == base_year]["employment"].sum()\n        latest_total = method_df[method_df["year"] == latest_year]["employment"].sum()\n        delta_abs = latest_total - base_total\n        delta_pct = (delta_abs / base_total * 100) if base_total else np.nan\n        method_metrics.append({\n            "method": method,\n            "base": base_total,\n            "latest": latest_total,\n            "delta": delta_abs,\n            "pct": delta_pct,\n        })\n\n    if not method_metrics:\n        st.info("Select at least one methodology to view results.")\n        return\n\n    cards_per_row = 3 if len(method_metrics) > 2 else len(method_metrics)
    for idx, metric in enumerate(method_metrics):\n        if idx % cards_per_row == 0:\n            cols = st.columns(cards_per_row)\n        render_method_card(\n            cols[idx % cards_per_row],\n            metric["method"],\n            metric["latest"],\n            metric["base"],\n            metric["delta"],\n            metric["pct"],\n            base_year,\n            latest_year,\n        )\n\n    summary_df = pd.DataFrame(method_metrics)\n    summary_df = summary_df.assign(\n        **{\n            f"Employment {base_year}": summary_df["base"],\n            f"Employment {latest_year}": summary_df["latest"],\n            "Abs change": summary_df["delta"],\n            "% change": summary_df["pct"],\n        }\n    )[\n        ["method", f"Employment {base_year}", f"Employment {latest_year}", "Abs change", "% change"]\n    ]\n    summary_df = summary_df.rename(columns={"method": "Methodology"})\n    summary_df["Abs change"] = summary_df["Abs change"].apply(format_number)\n    summary_df[f"Employment {base_year}"] = summary_df[f"Employment {base_year}"].apply(format_number)\n    summary_df[f"Employment {latest_year}"] = summary_df[f"Employment {latest_year}"].apply(format_number)\n    summary_df["% change"] = summary_df["% change"].apply(lambda v: f"{v:.1f}%" if not np.isnan(v) else "-")\n\n    with st.expander("Methodology comparison", expanded=False):\n        st.dataframe(summary_df.set_index("Methodology"), use_container_width=True)\n\n    st.caption("Source: data/processed/mi_occ_segment_totals_2024_2034.csv")\n\n\n'''

text, count = re.subn(pattern, new_block, text, count=1)
if count == 0:
    raise SystemExit('layout_overview pattern not found')

path.write_text(text, encoding='utf-8')
