from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
TEXT_SUFFIXES = {".html", ".js", ".json", ".md", ".mjs", ".ts", ".tsx"}
FORBIDDEN_NAMES = re.compile(r"(?<!VITE_LINZ_BASEMAPS_)(?:ARCGIS|OPENAI|LINZ)_API_KEY")
VITE_KEY = re.compile(r"VITE_[A-Z0-9_]*KEY")
SERVER_SECRET = re.compile(r"(?:sk-[A-Za-z0-9_-]{20,}|AAPK[A-Za-z0-9_-]{20,})")
ALLOWED_BROWSER_KEY = "VITE_LINZ_BASEMAPS_API_KEY"


def main() -> None:
    violations: list[str] = []
    for path in FRONTEND.rglob("*"):
        if not path.is_file() or (path.suffix not in TEXT_SUFFIXES and path.name != ".env.example"):
            continue
        if any(part in {"node_modules", "dist"} for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8")
        if FORBIDDEN_NAMES.search(text):
            violations.append(f"{path.relative_to(ROOT)}: server-side key name")
        if SERVER_SECRET.search(text):
            violations.append(f"{path.relative_to(ROOT)}: server-side secret literal")
        for match in VITE_KEY.findall(text):
            if match != ALLOWED_BROWSER_KEY:
                violations.append(f"{path.relative_to(ROOT)}: browser key {match}")
    if violations:
        raise SystemExit("Frontend secret boundary violations:\n" + "\n".join(violations))
    print(f"Frontend key boundary passed; only {ALLOWED_BROWSER_KEY} is allowed.")


if __name__ == "__main__":
    main()
