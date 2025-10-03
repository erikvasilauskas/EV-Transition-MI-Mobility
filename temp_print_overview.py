from pathlib import Path
text = Path('dashboards/occupation_forecast_dashboard.py').read_text(encoding='utf-8')
start = text.find('def layout_overview')
print(start)
print(text[start:start+400])
