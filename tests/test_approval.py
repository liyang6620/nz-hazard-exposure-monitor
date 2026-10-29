from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from nzhem.adapters.local.filesystem import LocalObjectStore, LocalStaticSitePublisher
from nzhem.adapters.local.sqlite import SqliteTableStore
from nzhem.core.agent.approval import ApprovalRejected, ApprovalService, ApprovalTokenSigner


class RecordingMailer:
    def __init__(self) -> None:
        self.messages: list[tuple[str, str, str]] = []

    def send(self, recipient: str, subject: str, text: str) -> None:
        self.messages.append((recipient, subject, text))


def service(tmp_path: Path) -> tuple[ApprovalService, SqliteTableStore, RecordingMailer]:
    objects = LocalObjectStore(tmp_path / "data")
    tables = SqliteTableStore(tmp_path / "state.db")
    mailer = RecordingMailer()
    return (
        ApprovalService(
            signer=ApprovalTokenSigner("test-key-that-is-at-least-32-bytes-long"),
            tables=tables,
            objects=objects,
            publisher=LocalStaticSitePublisher(objects),
            mailer=mailer,
        ),
        tables,
        mailer,
    )


def create_pending(approval: ApprovalService, now: datetime, *, map_image: bytes | None = None):
    return approval.create_pending(
        briefing_id="briefing-1",
        event_id="event-1",
        title="Test briefing",
        html="<h1>Approved</h1>",
        markdown="# Approved",
        map_image=map_image,
        recipient="owner@example.invalid",
        review_base_url="http://127.0.0.1:8000/review-briefing",
        now=now,
    )


def test_get_preview_does_not_mutate_and_post_approval_is_one_time(tmp_path: Path) -> None:
    approval, tables, mailer = service(tmp_path)
    now = datetime(2026, 10, 26, tzinfo=UTC)
    pending = create_pending(approval, now)

    preview = approval.preview(pending.approve_token, now)

    assert preview.action == "approve"
    assert tables.get_entity("briefings", "briefing", "briefing-1")["status"] == "pending"
    assert len(mailer.messages) == 1

    assert approval.decide(pending.approve_token, now, "127.0.0.1") == "approved"
    published = (tmp_path / "data/web/briefings/event-1.html").read_text(encoding="utf-8")
    assert "Approved" in published
    with pytest.raises(ApprovalRejected, match="invalid or unavailable"):
        approval.decide(pending.approve_token, now, "127.0.0.1")


def test_static_map_is_kept_with_draft_and_published_only_after_approval(tmp_path: Path) -> None:
    approval, tables, _ = service(tmp_path)
    now = datetime(2026, 10, 26, tzinfo=UTC)
    image = b"\x89PNG\r\n\x1a\nmap"
    pending = create_pending(approval, now, map_image=image)
    entity = tables.get_entity("briefings", "briefing", "briefing-1")
    assert entity["status"] == "pending"
    assert entity["published_map_path"].startswith("briefings/maps/")
    assert not (tmp_path / "data/web" / entity["published_map_path"]).exists()

    approval.decide(pending.approve_token, now, "127.0.0.1")

    published_map = tmp_path / "data/web" / entity["published_map_path"]
    published_html = tmp_path / "data/web/briefings/event-1.html"
    assert published_map.read_bytes() == image
    assert f"/{entity['published_map_path']}" in published_html.read_text(encoding="utf-8")


def test_tampered_expired_rejected_and_timeout_paths(tmp_path: Path) -> None:
    approval, tables, _ = service(tmp_path)
    now = datetime(2026, 10, 26, tzinfo=UTC)
    pending = create_pending(approval, now)

    with pytest.raises(ApprovalRejected, match="invalid or unavailable"):
        approval.preview(pending.approve_token + "x", now)
    with pytest.raises(ApprovalRejected, match="invalid or unavailable"):
        approval.preview(pending.reject_token, now + timedelta(hours=73))

    assert approval.expire_pending(now + timedelta(hours=73)) == 1
    assert tables.get_entity("briefings", "briefing", "briefing-1")["status"] == "expired"


def test_reject_does_not_publish(tmp_path: Path) -> None:
    approval, tables, _ = service(tmp_path)
    now = datetime(2026, 10, 26, tzinfo=UTC)
    pending = create_pending(approval, now, map_image=b"\x89PNG\r\n\x1a\nmap")
    entity = tables.get_entity("briefings", "briefing", "briefing-1")

    assert approval.decide(pending.reject_token, now, "127.0.0.1") == "rejected"
    assert tables.get_entity("briefings", "briefing", "briefing-1")["status"] == "rejected"
    assert not (tmp_path / "data/web/briefings/event-1.html").exists()
    assert not (tmp_path / "data/web" / entity["published_map_path"]).exists()


def test_superseded_revision_invalidates_both_review_links(tmp_path: Path) -> None:
    approval, tables, _ = service(tmp_path)
    now = datetime(2026, 10, 26, tzinfo=UTC)
    first = create_pending(approval, now)
    tables.upsert_entity(
        "briefings",
        {
            "PartitionKey": "briefing",
            "RowKey": "briefing-3",
            "briefing_id": "briefing-3",
            "event_id": "event-1",
            "revision": 3,
            "status": "approved",
            "created_at": now.isoformat(),
        },
    )

    assert approval.supersede_older_revisions(
        "event-1", keep_revision=3, now=now
    ) == 1
    entity = tables.get_entity("briefings", "briefing", "briefing-1")
    assert entity["status"] == "superseded"
    assert entity["superseded_by_revision"] == 3
    with pytest.raises(ApprovalRejected, match="invalid or unavailable"):
        approval.preview(first.approve_token, now)
    with pytest.raises(ApprovalRejected, match="invalid or unavailable"):
        approval.preview(first.reject_token, now)


def test_http_get_only_previews_and_post_executes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import hosts.local.app as local_app

    approval, tables, _ = service(tmp_path)
    now = datetime.now(UTC)
    pending = create_pending(approval, now)

    class Container:
        clock = type("Clock", (), {"now": lambda self: now})()

        def approval(self) -> ApprovalService:
            return approval

    monkeypatch.setattr(local_app, "container", Container())
    client = TestClient(local_app.app)
    response = client.get("/review-briefing", params={"token": pending.approve_token})

    assert response.status_code == 200
    assert "Confirm approve" in response.text
    assert tables.get_entity("briefings", "briefing", "briefing-1")["status"] == "pending"

    response = client.post("/review-briefing", params={"token": pending.approve_token})
    assert response.status_code == 200
    assert "Briefing approved" in response.text
    assert tables.get_entity("briefings", "briefing", "briefing-1")["status"] == "approved"

    replay = client.get("/review-briefing", params={"token": pending.approve_token})
    assert replay.status_code == 400
    assert replay.headers["content-type"].startswith("text/html")
    assert "Review link unavailable" in replay.text
    assert "detail" not in replay.text

    tampered = client.post("/review-briefing", params={"token": pending.approve_token + "x"})
    assert tampered.status_code == 400
    assert tampered.headers["content-type"].startswith("text/html")
    assert "Review link unavailable" in tampered.text
