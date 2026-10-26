from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nzhem.adapters.local.site_data import LocalSiteDataPublisher  # noqa: E402
from nzhem.adapters.local.sqlite import SqliteTableStore  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish versioned NZHEM website data")
    parser.add_argument("--event-root", type=Path, default=ROOT / ".local/data/curated/events/m3")
    parser.add_argument(
        "--reference-root",
        type=Path,
        default=ROOT / ".local/data/curated/reference-export/dee5b263952e",
    )
    parser.add_argument("--web-root", type=Path, default=ROOT / "frontend/public")
    parser.add_argument("--sqlite-path", type=Path, default=ROOT / ".local/state/nzhem.sqlite3")
    parser.add_argument("--generated-at", type=datetime.fromisoformat)
    arguments = parser.parse_args()

    publisher = LocalSiteDataPublisher(
        event_root=arguments.event_root,
        reference_root=arguments.reference_root,
        web_root=arguments.web_root,
        tables=SqliteTableStore(arguments.sqlite_path),
    )
    generated_at = arguments.generated_at or datetime.now(UTC)
    result = publisher.publish(generated_at.replace(tzinfo=generated_at.tzinfo or UTC))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
