from __future__ import annotations

import base64
import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import quote

from nzhem.ports import Mailer, ObjectStore, StaticSitePublisher, TableStore


class ApprovalRejected(RuntimeError):
    """Uniform rejection for invalid, expired or already-used review links."""


@dataclass(frozen=True)
class ReviewPreview:
    briefing_id: str
    title: str
    action: str


@dataclass(frozen=True)
class PendingBriefing:
    briefing_id: str
    approve_token: str
    reject_token: str
    expires_at: datetime


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


class ApprovalTokenSigner:
    def __init__(self, secret: str) -> None:
        if len(secret.encode("utf-8")) < 32:
            raise ValueError("Approval token key must contain at least 32 bytes")
        self._secret = secret.encode("utf-8")

    def issue(self, briefing_id: str, action: str, expires_at: datetime) -> str:
        if action not in {"approve", "reject"}:
            raise ValueError("Unsupported approval action")
        payload = _b64encode(
            json.dumps(
                {
                    "briefing_id": briefing_id,
                    "action": action,
                    "expires_at": expires_at.astimezone(UTC).isoformat(),
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        )
        signature = _b64encode(hmac.new(self._secret, payload.encode(), hashlib.sha256).digest())
        return f"{payload}.{signature}"

    def verify(self, token: str, now: datetime) -> dict[str, str]:
        try:
            payload, supplied = token.split(".", 1)
            expected = _b64encode(hmac.new(self._secret, payload.encode(), hashlib.sha256).digest())
            if not hmac.compare_digest(supplied, expected):
                raise ApprovalRejected("Review link is invalid or unavailable")
            decoded = json.loads(_b64decode(payload))
            if decoded["action"] not in {"approve", "reject"}:
                raise ApprovalRejected("Review link is invalid or unavailable")
            expires_at = datetime.fromisoformat(decoded["expires_at"])
            if now.astimezone(UTC) >= expires_at.astimezone(UTC):
                raise ApprovalRejected("Review link is invalid or unavailable")
            return decoded
        except ApprovalRejected:
            raise
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ApprovalRejected("Review link is invalid or unavailable") from exc


class ApprovalService:
    TABLE = "briefings"
    PARTITION = "briefing"

    def __init__(
        self,
        *,
        signer: ApprovalTokenSigner,
        tables: TableStore,
        objects: ObjectStore,
        publisher: StaticSitePublisher,
        mailer: Mailer,
    ) -> None:
        self._signer = signer
        self._tables = tables
        self._objects = objects
        self._publisher = publisher
        self._mailer = mailer

    def create_pending(
        self,
        *,
        briefing_id: str,
        event_id: str,
        title: str,
        html: str,
        markdown: str,
        map_image: bytes | None = None,
        recipient: str,
        review_base_url: str,
        now: datetime,
        needs_manual_review: bool = False,
        revision: int = 1,
        source_magnitude: float | None = None,
    ) -> PendingBriefing:
        expires_at = now.astimezone(UTC) + timedelta(hours=72)
        draft_root = f"drafts/{event_id}/{revision}"
        draft_map_path: str | None = None
        published_map_path: str | None = None
        if map_image is not None:
            draft_map_path = f"{draft_root}/map.png"
            published_map_path = (
                f"briefings/maps/{hashlib.sha256(briefing_id.encode('utf-8')).hexdigest()}.png"
            )
            self._objects.put_bytes("briefings", draft_map_path, map_image)
            map_section = (
                "<section><h2>Static event map</h2>"
                f"<img src='/{published_map_path}' "
                "alt='Static map centered on this earthquake event' "
                "width='800' height='500' loading='lazy'></section>"
            )
            if "</main></html>" in html:
                html = html.replace("</main></html>", map_section + "</main></html>", 1)
            else:
                html += map_section
            markdown += f"\n## Static event map\n\n![Event map](/{published_map_path})\n"
        self._objects.put_bytes("briefings", f"{draft_root}/index.html", html.encode())
        self._objects.put_bytes("briefings", f"{draft_root}/briefing.md", markdown.encode())
        entity: dict[str, Any] = {
            "PartitionKey": self.PARTITION,
            "RowKey": briefing_id,
            "briefing_id": briefing_id,
            "event_id": event_id,
            "revision": revision,
            "source_magnitude": source_magnitude,
            "title": title,
            "status": "pending",
            "needs_manual_review": needs_manual_review,
            "draft_html_path": f"{draft_root}/index.html",
            "draft_map_path": draft_map_path,
            "published_map_path": published_map_path,
            "created_at": now.astimezone(UTC).isoformat(),
            "expires_at": expires_at.isoformat(),
        }
        self._tables.upsert_entity(self.TABLE, entity)
        approve = self._signer.issue(briefing_id, "approve", expires_at)
        reject = self._signer.issue(briefing_id, "reject", expires_at)
        marker = "MANUAL REVIEW REQUIRED\n\n" if needs_manual_review else ""
        self._mailer.send(
            recipient,
            f"NZHEM briefing review: {title}",
            marker
            + markdown
            + "\n"
            + f"Approve: {review_base_url}?token={quote(approve)}\n"
            + f"Reject: {review_base_url}?token={quote(reject)}\n",
        )
        return PendingBriefing(briefing_id, approve, reject, expires_at)

    def preview(self, token: str, now: datetime) -> ReviewPreview:
        claims, entity = self._verified_pending(token, now)
        return ReviewPreview(entity["briefing_id"], entity["title"], claims["action"])

    def decide(self, token: str, now: datetime, source_ip: str) -> str:
        claims, entity = self._verified_pending(token, now)
        action = claims["action"]
        if action == "approve":
            document = self._objects.get_bytes("briefings", entity["draft_html_path"])
            if entity.get("draft_map_path"):
                map_image = self._objects.get_bytes("briefings", entity["draft_map_path"])
                self._publisher.publish(
                    str(entity["published_map_path"]),
                    map_image,
                )
            published_path = f"briefings/{entity['event_id']}.html"
            self._publisher.publish(published_path, document)
            self._publish_index(entity["event_id"], entity["title"], published_path)
            entity["status"] = "approved"
        else:
            entity["status"] = "rejected"
        entity["reviewed_at"] = now.astimezone(UTC).isoformat()
        entity["review_source_ip"] = source_ip
        entity["token_used"] = True
        self._tables.upsert_entity(self.TABLE, entity)
        return entity["status"]

    def expire_pending(self, now: datetime) -> int:
        return expire_pending_briefings(self._tables, now)

    def _verified_pending(self, token: str, now: datetime) -> tuple[dict[str, str], dict[str, Any]]:
        claims = self._signer.verify(token, now)
        entity = self._tables.get_entity(self.TABLE, self.PARTITION, claims["briefing_id"])
        if entity is None or entity.get("status") != "pending" or entity.get("token_used"):
            raise ApprovalRejected("Review link is invalid or unavailable")
        if now.astimezone(UTC) >= datetime.fromisoformat(entity["expires_at"]).astimezone(UTC):
            raise ApprovalRejected("Review link is invalid or unavailable")
        return claims, entity

    def _publish_index(self, event_id: str, title: str, path: str) -> None:
        try:
            entries = json.loads(self._objects.get_bytes("web", "briefings/index.json"))
        except FileNotFoundError:
            entries = []
        entries = [entry for entry in entries if entry["event_id"] != event_id]
        entries.append({"event_id": event_id, "title": title, "path": f"/{path}"})
        entries.sort(key=lambda entry: entry["event_id"])
        self._publisher.publish(
            "briefings/index.json",
            (json.dumps(entries, indent=2, sort_keys=True) + "\n").encode(),
        )


def expire_pending_briefings(tables: TableStore, now: datetime) -> int:
    count = 0
    for entity in tables.list_entities(ApprovalService.TABLE, ApprovalService.PARTITION):
        if entity["status"] != "pending":
            continue
        if now.astimezone(UTC) < datetime.fromisoformat(entity["expires_at"]).astimezone(UTC):
            continue
        entity["status"] = "expired"
        entity["expired_at"] = now.astimezone(UTC).isoformat()
        tables.upsert_entity(ApprovalService.TABLE, entity)
        count += 1
    return count
