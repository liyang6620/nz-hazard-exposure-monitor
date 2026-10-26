from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PBIP_ROOT = ROOT / "reports" / "powerbi"
TEXT_SUFFIXES = frozenset({".json", ".pbip", ".pbir", ".pbism", ".platform", ".tmdl"})
LOCAL_PATH_PATTERNS = (
    ("Windows drive path", re.compile(r"(?i)\b[a-z]:(?:[\\/]+)")),
    (
        "Windows UNC path",
        re.compile(r"(?:^|[\"'=\s])\\{2,}[a-z0-9][^\\/\r\n]*[\\/]", re.IGNORECASE),
    ),
    ("macOS user path", re.compile(r"(?i)/Users/[^/\s\"']+")),
    ("Linux user path", re.compile(r"(?i)/home/[^/\s\"']+")),
)


@dataclass(frozen=True)
class PortabilityFinding:
    path: Path
    line_number: int
    kind: str


def find_local_paths(root: Path = PBIP_ROOT) -> list[PortabilityFinding]:
    findings: list[PortabilityFinding] = []
    for path in sorted(candidate for candidate in root.rglob("*") if candidate.is_file()):
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8")
        for line_number, line in enumerate(text.splitlines(), start=1):
            for kind, pattern in LOCAL_PATH_PATTERNS:
                if pattern.search(line):
                    findings.append(PortabilityFinding(path, line_number, kind))
    return findings


def main() -> None:
    parser = argparse.ArgumentParser(description="Reject machine-local paths in PBIP sources")
    parser.add_argument("--root", type=Path, default=PBIP_ROOT)
    arguments = parser.parse_args()
    findings = find_local_paths(arguments.root.resolve())
    if findings:
        for finding in findings:
            try:
                display_path = finding.path.relative_to(ROOT)
            except ValueError:
                display_path = finding.path
            print(f"{display_path}:{finding.line_number}: {finding.kind}")
        raise SystemExit("PBIP contains a machine-local absolute path")
    print("PBIP portability check passed")


if __name__ == "__main__":
    main()
