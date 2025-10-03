from pathlib import Path
text = Path('dashboards/occupation_forecast_dashboard_v2.py').read_text(encoding='utf-8')
start = text.index('    st.markdown("\n**Objectives**: Provide a quick read on how Michigan\'s automotive workforce evolves under alternative growth assumptions.')
print(text[start:start+300])
