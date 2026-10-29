from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nzhem.adapters.local.filesystem import LocalObjectStore, LocalStaticSitePublisher  # noqa: E402
from nzhem.adapters.local.smtp import SmtpMailer  # noqa: E402
from nzhem.adapters.local.sqlite import SqliteTableStore  # noqa: E402
from nzhem.core.agent.approval import ApprovalService, ApprovalTokenSigner  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Invalidate superseded local briefing revisions")
    parser.add_argument("--sqlite-path", type=Path, default=ROOT / ".local/state/nzhem.sqlite3")
    parser.add_argument("--data-root", type=Path, default=ROOT / ".local/data")
    parser.add_argument("--keep-revision", type=int, required=True)
    parser.add_argument("event_ids", nargs="+")
    arguments = parser.parse_args()
    tables = SqliteTableStore(arguments.sqlite_path)
    objects = LocalObjectStore(arguments.data_root)
    service = ApprovalService(
        signer=ApprovalTokenSigner("local-supersede-only-key-32-bytes-minimum"),
        tables=tables,
        objects=objects,
        publisher=LocalStaticSitePublisher(objects),
        mailer=SmtpMailer("127.0.0.1", 1025, "nzhem@example.invalid"),
    )
    rows = list(tables.list_entities("briefings", "briefing"))
    now = datetime.now(UTC)
    result: dict[str, int] = {}
    for event_id in arguments.event_ids:
        kept = [
            row
            for row in rows
            if row.get("event_id") == event_id
            and int(row.get("revision", 1)) == arguments.keep_revision
        ]
        if not kept or kept[0].get("status") != "approved":
            raise RuntimeError(f"Revision {arguments.keep_revision} is not approved for {event_id}")
        result[event_id] = service.supersede_older_revisions(
            event_id, keep_revision=arguments.keep_revision, now=now
        )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
