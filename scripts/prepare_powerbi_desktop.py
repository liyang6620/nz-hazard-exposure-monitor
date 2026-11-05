"""Make an ignored PBIP copy with the machine-local data path for Desktop QA."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "reports/powerbi"
DESTINATION = ROOT / ".local/powerbi-desktop"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", default="powerbi-desktop")
    args = parser.parse_args()
    if not args.name.startswith("powerbi-desktop") or any(c in args.name for c in "/\\:"):
        raise ValueError("Desktop copy must stay under .local with a powerbi-desktop name")
    destination = ROOT / ".local" / args.name
    if destination.exists():
        if destination.resolve().parent != (ROOT / ".local").resolve():
            raise RuntimeError("Unsafe Power BI validation directory")
        shutil.rmtree(destination)
    shutil.copytree(SOURCE, destination)
    expression = destination / "nzhem.SemanticModel/definition/expressions.tmdl"
    content = expression.read_text(encoding="utf-8")
    marker = 'expression RepoRoot = "..\\\\.."'
    if marker not in content:
        raise RuntimeError("Source RepoRoot expression changed; inspect before local substitution")
    local_root = str(ROOT)
    expression.write_text(
        content.replace(marker, f'expression RepoRoot = "{local_root}"'),
        encoding="utf-8",
    )
    print("Prepared ignored Power BI Desktop copy; source-controlled PBIP is unchanged")


if __name__ == "__main__":
    main()
