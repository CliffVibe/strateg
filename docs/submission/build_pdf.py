"""Описание работы → PDF: docs/06-submission.md → docs/submission/opisanie-raboty.pdf (Edge headless, stdlib).
Запуск из корня репозитория: python docs/submission/build_pdf.py"""
import html
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import strat  # noqa: E402  — тот же Markdown → HTML, что у report.html

SRC = ROOT / "docs" / "06-submission.md"
OUT = ROOT / "docs" / "submission"
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
CSS = """
@page { size: A4; margin: 14mm 13mm 16mm; }
body { font: 10.5pt/1.45 'Segoe UI', Arial, sans-serif; color: #1d1d1f; }
h1 { font-size: 21pt; margin: 0 0 4px; } h2 { font-size: 15pt; margin: 20px 0 6px; border-bottom: 2px solid #e3e3e8;
  padding-bottom: 3px; break-after: avoid; } h3 { font-size: 12pt; margin: 14px 0 4px; break-after: avoid; }
p { margin: 5px 0; } ul { margin: 4px 0 4px 18px; padding: 0; } li { margin: 2px 0; }
table { border-collapse: collapse; width: 100%; margin: 8px 0; font-size: 9pt; break-inside: auto; }
th, td { border: 1px solid #d4d4da; padding: 4px 6px; vertical-align: top; text-align: left; } th { background: #f2f2f6; }
tr { break-inside: avoid; } code { font: 9pt Consolas, monospace; background: #f2f2f6; padding: 0 3px; border-radius: 3px; }
a { color: #0b57d0; text-decoration: none; }
figure { margin: 10px 0 14px; break-inside: avoid; } figure img { max-width: 100%; max-height: 205mm; border: 1px solid #d4d4da; display: block; }
figcaption { font-size: 8.8pt; color: #5a5a66; margin-top: 3px; }
"""


def build() -> Path:
    md = SRC.read_text(encoding="utf-8")
    md = re.sub(r"\n {2,}(?![-*]\s|\d+\.\s)(?=\S)", " ", md)  # перенос строки внутри пункта списка — та же строка
    parts = []
    for chunk in re.split(r"^(!\[.*?\]\(.*?\))\s*$", md, flags=re.M):
        if m := re.match(r"!\[(.*?)\]\((.*?)\)$", chunk.strip()):
            img = (SRC.parent / m.group(2)).resolve()
            parts.append(f'<figure><img src="{img.as_uri()}"><figcaption>{html.escape(m.group(1))}</figcaption></figure>')
        else:
            parts.append(strat.md_to_html(chunk, {}, {}))
    page = OUT / "opisanie-raboty.html"
    page.write_text(f'<!doctype html><html lang="ru"><meta charset="utf-8"><title>Стратег продукта — описание работы</title>'
                    f"<style>{CSS}</style><body>{''.join(parts)}</body></html>", encoding="utf-8")
    pdf = OUT / "opisanie-raboty.pdf"
    subprocess.run([str(EDGE), "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={pdf}", page.as_uri()], check=True, capture_output=True)
    page.unlink()
    return pdf


if __name__ == "__main__":
    p = build()
    print(p.relative_to(ROOT), p.stat().st_size // 1024, "КБ")
