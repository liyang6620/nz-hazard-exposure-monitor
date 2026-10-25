from __future__ import annotations

import hashlib
import json
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import requests

from nzhem.adapters.local.briefing_tools import DuckDbBriefingTools
from nzhem.adapters.local.filesystem import LocalObjectStore, LocalStaticSitePublisher
from nzhem.adapters.local.smtp import SmtpMailer
from nzhem.adapters.local.sqlite import SqliteTableStore
from nzhem.core.agent.approval import ApprovalRejected, ApprovalService, ApprovalTokenSigner
from nzhem.core.agent.briefing import DraftBriefingService
from nzhem.core.agent.schemas import LIMITATIONS

ROOT = Path(__file__).resolve().parents[1]


class DeterministicBriefingLlm:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def generate(self, *args: Any, **kwargs: Any) -> str:
        return json.dumps(self._payload)


def create_pending(
    service: ApprovalService,
    *,
    briefing_id: str,
    event_id: str,
    now: datetime,
    html: str | None = None,
    markdown: str | None = None,
):
    return service.create_pending(
        briefing_id=briefing_id,
        event_id=event_id,
        title=f"NZHEM briefing {event_id}",
        html=html or f"<!doctype html><h1>NZHEM briefing {event_id}</h1>",
        markdown=markdown or f"# NZHEM briefing {event_id}\n",
        recipient="owner@example.invalid",
        review_base_url="http://127.0.0.1:8000/review-briefing",
        now=now,
    )


def render_kaikoura_draft() -> tuple[str, str, bool]:
    tools = DuckDbBriefingTools(
        ROOT / ".local/data/curated/events/m3",
        ROOT / ".local/data/curated/reference-export/dee5b263952e",
    )
    try:
        event = tools.get_event("2016p858000")
        exposure = tools.get_exposure_summary("2016p858000", 6.0)
        top = exposure[0]
        payload = {
            "headline": "Kaikoura earthquake exposure briefing",
            "key_figures": [
                {
                    "label": "Magnitude",
                    "value": event["magnitude"],
                    "unit": "M",
                    "source_tool": "get_event",
                    "source_field": "magnitude",
                },
                {
                    "label": "Buildings in the most affected region",
                    "value": top["buildings"],
                    "unit": "buildings",
                    "source_tool": "get_exposure_summary",
                    "source_field": "buildings",
                },
                {
                    "label": "Population in the most affected region",
                    "value": top["population_2023"],
                    "unit": "people",
                    "source_tool": "get_exposure_summary",
                    "source_field": "population_2023",
                },
            ],
            "regions_most_affected": [top["region_name"]],
            "then_vs_now": "Event-time building exposure is not supported for this event.",
            "limitations": list(LIMITATIONS),
            "recommended_checks": ["Review official emergency information."],
            "generated_at": datetime.now(UTC).isoformat(),
        }
        draft = DraftBriefingService(
            tools,
            DeterministicBriefingLlm(payload),
            max_output_tokens=1200,
            total_token_limit=12000,
        ).draft("2016p858000")
        return draft.html, draft.markdown, draft.fidelity_passed
    finally:
        tools.close()


def run_demo(output_path: Path) -> dict:
    run_id = uuid.uuid4().hex
    root = ROOT / ".local" / "m6-workflow-demo" / run_id
    objects = LocalObjectStore(root / "data")
    tables = SqliteTableStore(root / "state.sqlite3")
    service = ApprovalService(
        signer=ApprovalTokenSigner(secrets.token_urlsafe(48)),
        tables=tables,
        objects=objects,
        publisher=LocalStaticSitePublisher(objects),
        mailer=SmtpMailer("127.0.0.1", 1025, "nzhem@example.invalid"),
    )
    now = datetime.now(UTC).replace(microsecond=0)
    mailpit_before = requests.get("http://127.0.0.1:8025/api/v1/messages", timeout=10)
    mailpit_before.raise_for_status()
    mailpit_count_before = int(mailpit_before.json()["total"])
    html, markdown, draft_fidelity = render_kaikoura_draft()

    approved = create_pending(
        service,
        briefing_id="approve-demo",
        event_id="2016p858000",
        now=now,
        html=html,
        markdown=markdown,
    )
    preview = service.preview(approved.approve_token, now)
    status_after_get = tables.get_entity("briefings", "briefing", "approve-demo")["status"]
    status_after_post = service.decide(
        approved.approve_token, now + timedelta(seconds=1), "127.0.0.1"
    )
    try:
        service.decide(approved.approve_token, now + timedelta(seconds=2), "127.0.0.1")
        replay_rejected = False
    except ApprovalRejected:
        replay_rejected = True

    rejected = create_pending(service, briefing_id="reject-demo", event_id="2014p051675", now=now)
    rejected_status = service.decide(rejected.reject_token, now + timedelta(seconds=1), "127.0.0.1")

    expired = create_pending(service, briefing_id="expire-demo", event_id="2026p776286", now=now)
    expired_count = service.expire_pending(now + timedelta(hours=73))
    try:
        service.preview(expired.approve_token, now + timedelta(hours=73))
        expired_token_rejected = False
    except ApprovalRejected:
        expired_token_rejected = True

    published = objects.get_bytes("web", "briefings/2016p858000.html")
    index = json.loads(objects.get_bytes("web", "briefings/index.json"))
    mailpit = requests.get("http://127.0.0.1:8025/api/v1/messages", timeout=10)
    mailpit.raise_for_status()
    mail_payload = mailpit.json()
    result = {
        "run_id": run_id,
        "get_preview_action": preview.action,
        "draft_numeric_fidelity_passed": draft_fidelity,
        "status_after_get": status_after_get,
        "status_after_approval_post": status_after_post,
        "approval_token_replay_rejected": replay_rejected,
        "rejection_status": rejected_status,
        "rejected_event_published": (root / "data/web/briefings/2014p051675.html").exists(),
        "expired_count": expired_count,
        "expired_token_rejected": expired_token_rejected,
        "approved_page_sha256": hashlib.sha256(published).hexdigest(),
        "published_index_entries": len(index),
        "mailpit_messages_added": int(mail_payload["total"]) - mailpit_count_before,
        "mailpit_loopback_only": True,
        "tokens_recorded_in_evidence": False,
    }
    safe_mailpit = root / "safe-mailpit.html"
    subjects = [
        str(message.get("Subject", "NZHEM briefing review"))
        for message in mail_payload.get("messages", [])[:3]
    ]
    rows = "".join(
        f"<tr><td>nzhem@example.invalid</td><td>owner@example.invalid</td><td>{subject}</td></tr>"
        for subject in subjects
    )
    safe_mailpit.write_text(
        "<!doctype html><meta charset='utf-8'><title>Mailpit delivery evidence</title>"
        "<style>body{font-family:Segoe UI,sans-serif;margin:40px;color:#17211b}"
        "table{border-collapse:collapse;width:100%}th,td{border-bottom:1px solid #ccd6d1;"
        "padding:14px;text-align:left}h1{letter-spacing:0}</style>"
        "<h1>Local Mailpit delivery</h1>"
        f"<p>{result['mailpit_messages_added']} review messages added over loopback SMTP.</p>"
        "<table><thead><tr><th>From</th><th>To</th><th>Subject</th></tr></thead>"
        f"<tbody>{rows}</tbody></table><p>Message bodies and approval tokens are omitted.</p>",
        encoding="utf-8",
    )
    result["sanitized_mailpit_view"] = str(safe_mailpit.relative_to(ROOT)).replace("\\", "/")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(run_demo(ROOT / "evidence/m6/workflow-demo.json"), sort_keys=True))
