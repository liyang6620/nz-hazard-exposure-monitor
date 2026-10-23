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
    def generate(self, prompt: str, *, max_output_tokens: int) -> str: ...


class StaticSitePublisher(Protocol):
    def publish(self, path: str, content: bytes) -> None: ...


class EventSource(Protocol):
    def fetch_updated_after(self, updated_after: datetime) -> Sequence[Mapping[str, Any]]: ...
