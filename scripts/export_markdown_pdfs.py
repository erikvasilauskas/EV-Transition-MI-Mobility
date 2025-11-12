from pathlib import Path

from fpdf import FPDF

FILES = [
    ("docs/occupation_forecast_methodology.md", "reports/occupation_forecast_methodology.pdf"),
    ("docs/sam_auto_methods.md", "reports/sam_auto_methods.pdf"),
    ("reports/appendix_employment_projection_methods.md", "reports/appendix_employment_projection_methods.pdf"),
]


def main() -> None:
    for src_path, dest_path in FILES:
        src = Path(src_path)
        dest = Path(dest_path)
        text = src.read_text(encoding="utf-8")
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_font("Courier", size=10)
        for line in text.splitlines():
            if not line.strip():
                pdf.ln(5)
                continue
            safe_line = line.encode("latin-1", "replace").decode("latin-1")
            pdf.multi_cell(0, 5, safe_line)
        dest.parent.mkdir(parents=True, exist_ok=True)
        pdf.output(dest_path)


if __name__ == "__main__":
    main()
