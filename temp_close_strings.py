from pathlib import Path

path = Path("dashboards/occupation_forecast_dashboard_v2.py")
text = path.read_text(encoding="utf-8")
text = text.replace('\n")\n', '\n""")\n')
path.write_text(text, encoding="utf-8")
