"""Make an ignored PBIP copy with the machine-local data path for Desktop QA."""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "reports/powerbi"
DESTINATION = ROOT / ".local/powerbi-desktop"


def main() -> None:
    if DESTINATION.exists():
        if DESTINATION.resolve().parent != (ROOT / ".local").resolve():
            raise RuntimeError("Unsafe Power BI validation directory")
        shutil.rmtree(DESTINATION)
    shutil.copytree(SOURCE, DESTINATION)
    expression = DESTINATION / "nzhem.SemanticModel/definition/expressions.tmdl"
    content = expression.read_text(encoding="utf-8")
    marker = 'Value = "..\\\\.."'
    if marker not in content:
        raise RuntimeError("Source RepoRoot expression changed; inspect before local substitution")
    local_root = str(ROOT)
    expression.write_text(content.replace(marker, f'Value = "{local_root}"'), encoding="utf-8")
    print("Prepared ignored Power BI Desktop copy; source-controlled PBIP is unchanged")


if __name__ == "__main__":
    main()
