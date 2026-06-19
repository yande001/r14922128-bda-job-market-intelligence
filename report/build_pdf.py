"""Build report/r14922128.pdf from report/report.md.

Pipeline: Markdown -> styled HTML -> PDF (via LibreOffice headless).
Run from repo root:  python3 report/build_pdf.py
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FIGDIR = os.path.join(ROOT, "docs", "figures")
STUDENT_ID = "r14922128"

CSS = """
@page { size: A4; margin: 1.8cm; }
body { font-family: 'Noto Sans CJK TC','DejaVu Sans',sans-serif; font-size: 10.5pt;
       line-height: 1.5; color: #1e293b; }
h1 { color: #0f766e; font-size: 21pt; margin-bottom: 2pt; }
h2 { color: #0f766e; font-size: 15pt; border-bottom: 2px solid #0f766e;
     padding-bottom: 3px; margin-top: 20px; }
h3 { color: #334155; font-size: 12.5pt; margin-bottom: 2pt; }
h4 { color: #475569; font-size: 11pt; }
table { border-collapse: collapse; width: 100%; margin: 10px 0; font-size: 9.5pt; }
th, td { border: 1px solid #cbd5e1; padding: 5px 8px; text-align: left; }
th { background: #f0fdfa; color: #0f766e; }
code { background: #f1f5f9; padding: 1px 4px; border-radius: 3px; font-size: 9pt; }
pre { background: #f8fafc; border: 1px solid #e2e8f0; padding: 8px; border-radius: 4px;
      font-size: 8.5pt; overflow-wrap: break-word; white-space: pre-wrap; }
img { max-width: 100%; margin: 8px 0; }
hr { border: none; border-top: 1px solid #cbd5e1; margin: 14px 0; }
a { color: #0f766e; }
"""


def main():
    try:
        import markdown
    except ImportError:
        raise SystemExit("pip install markdown")

    with open(os.path.join(HERE, "report.md"), encoding="utf-8") as f:
        md_text = f.read()

    # point figures at absolute file URIs
    md_text = md_text.replace("FIGDIR", "file://" + FIGDIR)

    html_body = markdown.markdown(
        md_text, extensions=["tables", "fenced_code", "sane_lists"]
    )
    # Images keep their intrinsic (DPI-based) size; LibreOffice scales any that
    # exceed the text width down to fit, giving full-width, readable figures.

    html = f"<!DOCTYPE html><html><head><meta charset='utf-8'><style>{CSS}</style>" \
           f"</head><body>{html_body}</body></html>"

    html_path = os.path.join(HERE, "report.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        raise SystemExit("LibreOffice (soffice) not found; cannot render PDF.")

    # HTML -> ODT (Writer engine) -> PDF avoids the writer_web blank-page quirk.
    for fmt in ("odt", "pdf"):
        src_in = html_path if fmt == "odt" else os.path.join(HERE, "report.odt")
        subprocess.run(
            [soffice, "--headless", "--convert-to", fmt, "--outdir", HERE, src_in],
            check=True, cwd=ROOT,
        )
    src = os.path.join(HERE, "report.pdf")
    dst = os.path.join(HERE, f"{STUDENT_ID}.pdf")
    if os.path.exists(src):
        shutil.copyfile(src, dst)
    print("wrote", dst)


if __name__ == "__main__":
    main()
