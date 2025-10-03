from pathlib import Path
import re

path = Path('dashboards/occupation_forecast_dashboard.py')
text = path.read_text()

if 'import json' not in text:
    text = text.replace('from typing import List\n\nimport numpy as np', 'from typing import List\nimport json\n\nimport numpy as np', 1)

pattern = 'DEFAULT_METHOD = "lightcast_moody"\n'
replacement = 'DEFAULT_METHOD = "lightcast_moody"\nCOLORS_PATH = REPO_ROOT / "config" / "colors.json"\nwith open(COLORS_PATH, "r", encoding="utf-8") as _f:\n    COLORS = json.load(_f)\nTEAL = COLORS.get("teal", "#2B9CB4")\n\n'
if 'COLORS_PATH' not in text:
    text = text.replace(pattern, replacement, 1)

card_function = '\n\ndef render_method_card(container, method_name: str, latest: float, base: float, delta: float, delta_pct: float, base_year: int, latest_year: int) -> None:\n    delta_text = format_number(delta)\n    pct_text = f" ({delta_pct:.1f}%)" if not np.isnan(delta_pct) else ""\n    container.markdown(\n        f"""\n        <div style=\\"background-color:#F5F9FA;padding:16px;border-radius:10px;border-left:4px solid {TEAL};\\">\n            <div style=\\"font-size:0.85rem;color:#4A5568;margin-bottom:4px;\\">{method_name}</div>\n            <div style=\\"font-size:2rem;font-weight:600;color:#1A202C;\\">{format_number(latest)}<span style=\\"font-size:1rem;font-weight:400;color:#718096;\\"> ({latest_year})</span></div>\n            <div style=\\"font-size:0.95rem;font-weight:500;color:{TEAL};margin-top:6px;\\">Δ {delta_text}{pct_text}</div>\n            <div style=\\"font-size:0.8rem;color:#718096;margin-top:4px;\\">Baseline {base_year}: {format_number(base)}</div>\n        </div>\n        """,\n        unsafe_allow_html=True,\n    )\n\n'
if 'def render_method_card' not in text:
    text = text.replace('@st.cache_data(show_spinner=False)\ndef load_core_series()', card_function + '@st.cache_data(show_spinner=False)\ndef load_core_series()', 1)

path.write_text(text, encoding='utf-8')
