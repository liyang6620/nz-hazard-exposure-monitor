"""Crop Desktop's recovery banner and render the five report canvases."""

from __future__ import annotations

import argparse
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--output-dir", type=Path, default=EVIDENCE)
    args = parser.parse_args()
    sources = sorted(SOURCE_ROOT.glob("print-job-*/nzhem.pdf"), key=lambda p: p.stat().st_mtime)
    source = args.source or (sources[-1] if sources else None)
    if source is None:
        raise FileNotFoundError("Power BI Desktop PDF export not found")
    reader = PdfReader(source)
    if len(reader.pages) != len(PAGES):
        raise ValueError(f"Expected {len(PAGES)} report pages, found {len(reader.pages)}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / "nzhem-powerbi-report.pdf"
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
                str(args.output_dir / name),
            ],
            check=True,
        )
    print(f"Finalized {len(PAGES)} Desktop report pages from {source.parent.name}")


if __name__ == "__main__":
    main()
