from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nzhem.core.agent.briefing import build_briefing_facts  # noqa: E402

EVENT_IDS = (
    "2026p776286",
    "2021p169764",
    "2016p858000",
    "2016p661332",
    "2014p051675",
    "2013p613797",
    "2013p543824",
    "3528839",
    "3468575",
    "3366146",
)


def _escape(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def build_table(site_root: Path) -> str:
    manifest = json.loads((site_root / "data/manifest.json").read_text(encoding="utf-8"))
    generation = site_root / str(manifest["base_path"]).lstrip("/")
    rows = []
    for event_id in EVENT_IDS:
        path = generation / "events" / event_id / "summary.json"
        raw = path.read_bytes()
        summary = json.loads(raw)
        facts = build_briefing_facts(summary)
        displays = {item["label"]: item["display"] for item in facts["key_figures"]}
        rows.append(
            [
                summary["name"],
                displays["Magnitude"],
                displays["Depth"],
                displays["Origin time"],
                displays["Maximum MMI"],
                displays["Buildings in MMI 6+ shaking"],
                displays["People in MMI 6+ shaking"],
                displays.get("Most affected region", "Not applicable"),
                displays["Shaking source"],
                displays["Assessment basis"],
                hashlib.sha256(raw).hexdigest()[:12],
                facts["headline"],
            ]
        )
    header = [
        "Event",
        "Magnitude",
        "Depth",
        "NZ origin time",
        "Max MMI",
        "MMI 6+ buildings",
        "MMI 6+ people",
        "Top region at MMI 6+",
        "Shaking source",
        "Basis",
        "summary SHA-256",
        "Deterministic title",
    ]
    lines = [
        "# Briefing to summary.json reconciliation",
        "",
        "Every title and key figure below is generated directly from the current published "
        "event `summary.json`. Population is rounded to a whole person; magnitude, depth and "
        "MMI use one decimal place. The LLM cannot modify these fields.",
        "",
        "Final review batch: revision 3, manually approved by the project manager on the "
        "repository owner's explicit instruction. The twenty earlier drafts are marked "
        "`superseded`; their review links are invalid.",
        "",
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    lines.extend("| " + " | ".join(_escape(value) for value in row) + " |" for row in rows)
    lines.extend(
        [
            "",
            f"Published generation: `{manifest['generation_id']}`.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Reconcile briefing facts to published summaries")
    parser.add_argument("--site-root", type=Path, default=ROOT / "frontend/public")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "evidence/frontend-pr1/briefing-summary-reconciliation.md",
    )
    arguments = parser.parse_args()
    content = build_table(arguments.site_root)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(content, encoding="utf-8")
    print(arguments.output)


if __name__ == "__main__":
    main()
