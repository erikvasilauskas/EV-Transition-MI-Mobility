from pathlib import Path
text = Path("dashboards/occupation_forecast_dashboard_v2.py").read_text(encoding="utf-8")
start = text.index("    st.markdown(\"")
end = text.index("\")\n", start) + len("\")\n")
print(repr(text[start:end]))
