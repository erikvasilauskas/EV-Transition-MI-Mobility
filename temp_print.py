from pathlib import Path
text = Path('scripts/occupation_forecasts_from_segment_totals.py').read_text(encoding='utf-8')
start = text.index('def build_forecasts')
end = text.index('def layout_occupation_insights')
print(text[start:end])
