"""Rebuild the original one-page PDF fixture from its supplied Markdown."""

from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "fixtures/public/windmill-field-notes.md"
OUTPUT = ROOT / "fixtures/public/windmill-field-notes.pdf"
FONT_ROOT = Path("/usr/share/fonts/truetype/dejavu")


def main() -> None:
    pdfmetrics.registerFont(TTFont("DejaVu", str(FONT_ROOT / "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont("DejaVu-Bold", str(FONT_ROOT / "DejaVuSans-Bold.ttf")))
    lines = [line.strip() for line in SOURCE.read_text(encoding="utf-8").splitlines() if line.strip()]
    document = canvas.Canvas(str(OUTPUT), pagesize=letter, invariant=1)
    document.setTitle("North Mill Field Notes")
    document.setAuthor("COMPOSITOR project fixture")
    y = 730
    for line in lines:
        if line.startswith("# "):
            document.setFont("DejaVu-Bold", 18)
            document.drawString(72, y, line[2:])
            y -= 50
        elif line.startswith("## "):
            document.setFont("DejaVu-Bold", 12)
            document.drawString(72, y, line[3:])
            y -= 22
        else:
            document.setFont("DejaVu", 10)
            document.drawString(72, y, line)
            y -= 46
    document.setFont("DejaVu", 9)
    document.drawString(72, 55, "Project-authored COMPOSITOR engineering fixture | Page 1")
    document.showPage()
    document.save()


if __name__ == "__main__":
    main()
