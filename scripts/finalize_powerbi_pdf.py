"""Crop Desktop's recovery banner and render the five report canvases."""

from __future__ import annotations

import subprocess
from pathlib import Path

from pypdf import PdfReader, PdfWriter

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/m5"
SOURCE_ROOT = Path.home() / "AppData/Local/Temp/Power BI Desktop"
PAGES = [
    "event-overview",
    "event-comparison",
    "regional-exposure",
    "event-history",
    "data-health",
]


def main() -> None:
    sources = sorted(SOURCE_ROOT.glob("print-job-*/nzhem.pdf"), key=lambda p: p.stat().st_mtime)
    if not sources:
        raise FileNotFoundError("Power BI Desktop PDF export not found")
    reader = PdfReader(sources[-1])
    if len(reader.pages) != len(PAGES):
        raise ValueError(f"Expected {len(PAGES)} report pages, found {len(reader.pages)}")
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    output = EVIDENCE / "nzhem-powerbi-report.pdf"
    writer = PdfWriter()
    for page in reader.pages:
        # Desktop exported its 43 pt auto-recovery notice above the report canvas.
        page.cropbox.upper_right = (page.cropbox.right, page.cropbox.top - 43)
        page.mediabox.upper_right = (page.mediabox.right, page.mediabox.top - 43)
        writer.add_page(page)
    with output.open("wb") as stream:
        writer.write(stream)
    for index, name in enumerate(PAGES, start=1):
        subprocess.run(
            [
                "pdftoppm",
                "-f",
                str(index),
                "-l",
                str(index),
                "-singlefile",
                "-r",
                "120",
                "-png",
                str(output),
                str(EVIDENCE / name),
            ],
            check=True,
        )
    print(f"Finalized {len(PAGES)} Desktop report pages from {sources[-1].parent.name}")


if __name__ == "__main__":
    main()
