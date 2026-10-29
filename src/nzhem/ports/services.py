from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol


class Clock(Protocol):
    def now(self) -> datetime: ...


class ObjectStore(Protocol):
    def put_bytes(self, container: str, path: str, data: bytes) -> None: ...

    def get_bytes(self, container: str, path: str) -> bytes: ...


@dataclass(frozen=True)
class QueueMessage:
    message_id: int | str
    payload: Mapping[str, Any]
    dequeue_count: int
    receipt: str


class QueueStore(Protocol):
    def send(self, queue_name: str, payload: Mapping[str, Any]) -> int | str: ...

    def receive(self, queue_name: str) -> QueueMessage | None: ...

    def complete(self, queue_name: str, message_id: int | str, receipt: str) -> None: ...

    def abandon(self, queue_name: str, message_id: int | str, receipt: str) -> None: ...


class TableStore(Protocol):
    def upsert_entity(self, table_name: str, entity: Mapping[str, Any]) -> None: ...

    def get_entity(
        self, table_name: str, partition_key: str, row_key: str
    ) -> dict[str, Any] | None: ...

    def list_entities(
        self, table_name: str, partition_key: str | None = None
    ) -> Sequence[dict[str, Any]]: ...


class SecretStore(Protocol):
    def get_secret(self, name: str) -> str: ...


class Mailer(Protocol):
    def send(self, recipient: str, subject: str, text: str) -> None: ...


class LlmClient(Protocol):
    def generate(
        self,
        prompt: str,
        *,
        max_output_tokens: int,
        response_schema: Mapping[str, Any] | None = None,
    ) -> str: ...


class StaticSitePublisher(Protocol):
    def publish(self, path: str, content: bytes) -> None: ...


class SiteDataPublisher(Protocol):
    def publish(self, generated_at: datetime) -> Mapping[str, Any]: ...


class StaticMapProvider(Protocol):
    """Server-side provider for an optional briefing map attachment.

    The core package only knows this narrow port.  Authentication and the
    remote protocol belong to an adapter, so browser hosts never receive a
    provider or its credential.
    """

    def render(
        self,
        *,
        briefing_id: str,
        longitude: float,
        latitude: float,
    ) -> bytes: ...


class EventSource(Protocol):
    def fetch_updated_after(self, updated_after: datetime) -> Sequence[Mapping[str, Any]]: ...


class EventAssessor(Protocol):
    """Turn one catalogue event into a terminal exposure assessment."""

    def assess(self, event: Mapping[str, Any], assessed_at: datetime) -> Mapping[str, Any]: ...


@dataclass(frozen=True)
class ReferenceRefreshResult:
    source_buildings: int
    curated_buildings: int
    source_population: int
    allocated_population: float
    rejected_buildings: int
    suppressed_sa1: int
    elapsed_seconds: float
    peak_rss_mb: float
    minimum_free_disk_gb: float
    output_hashes: Mapping[str, str]


class ReferenceDataRefresher(Protocol):
    def refresh(self) -> ReferenceRefreshResult: ...
