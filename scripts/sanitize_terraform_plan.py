from __future__ import annotations

import re
import sys

GUID = re.compile(
    r"(?i)\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b"
)
EMAIL = re.compile(r"(?i)\b[^\s@]+@[^\s@]+\.[^\s@]+\b")


def main() -> None:
    content = sys.stdin.read()
    content = GUID.sub("[REDACTED-GUID]", content)
    content = EMAIL.sub("[REDACTED-EMAIL]", content)
    sys.stdout.write(content)


if __name__ == "__main__":
    main()
