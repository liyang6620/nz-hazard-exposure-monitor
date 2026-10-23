from __future__ import annotations

import json
import sqlite3
import time
import uuid
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from nzhem.ports import QueueMessage


class _SqliteStore:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._initialise()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path, timeout=10, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 10000")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def _initialise(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS table_entities (
                    table_name TEXT NOT NULL,
                    partition_key TEXT NOT NULL,
                    row_key TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    updated_at REAL NOT NULL,
                    PRIMARY KEY (table_name, partition_key, row_key)
                );
                CREATE TABLE IF NOT EXISTS queue_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    queue_name TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    visible_at REAL NOT NULL,
                    dequeue_count INTEGER NOT NULL DEFAULT 0,
                    receipt TEXT,
                    created_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_queue_visible
                    ON queue_messages(queue_name, visible_at, id);
                """
            )


class SqliteTableStore(_SqliteStore):
    def upsert_entity(self, table_name: str, entity: Mapping[str, Any]) -> None:
        partition_key = str(entity["PartitionKey"])
        row_key = str(entity["RowKey"])
        payload = json.dumps(dict(entity), sort_keys=True, separators=(",", ":"))
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO table_entities
                    (table_name, partition_key, row_key, payload, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(table_name, partition_key, row_key) DO UPDATE SET
                    payload = excluded.payload,
                    updated_at = excluded.updated_at
                """,
                (table_name, partition_key, row_key, payload, time.time()),
            )

    def get_entity(
        self, table_name: str, partition_key: str, row_key: str
    ) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT payload FROM table_entities
                WHERE table_name = ? AND partition_key = ? AND row_key = ?
                """,
                (table_name, partition_key, row_key),
            ).fetchone()
        return json.loads(row["payload"]) if row else None

    def list_entities(
        self, table_name: str, partition_key: str | None = None
    ) -> Sequence[dict[str, Any]]:
        query = "SELECT payload FROM table_entities WHERE table_name = ?"
        parameters: tuple[str, ...] = (table_name,)
        if partition_key is not None:
            query += " AND partition_key = ?"
            parameters = (table_name, partition_key)
        query += " ORDER BY partition_key, row_key"
        with self._connect() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [json.loads(row["payload"]) for row in rows]


class SqliteQueueStore(_SqliteStore):
    def __init__(
        self,
        path: Path,
        *,
        visibility_timeout_seconds: int = 30,
        max_dequeue_count: int = 3,
        timestamp: Callable[[], float] = time.time,
    ) -> None:
        self._visibility_timeout_seconds = visibility_timeout_seconds
        self._max_dequeue_count = max_dequeue_count
        self._timestamp = timestamp
        super().__init__(path)

    def send(self, queue_name: str, payload: Mapping[str, Any]) -> int:
        encoded = json.dumps(dict(payload), sort_keys=True, separators=(",", ":"))
        now = self._timestamp()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO queue_messages
                    (queue_name, payload, visible_at, dequeue_count, created_at)
                VALUES (?, ?, ?, 0, ?)
                """,
                (queue_name, encoded, now, now),
            )
        return int(cursor.lastrowid)

    def receive(self, queue_name: str) -> QueueMessage | None:
        now = self._timestamp()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._move_exhausted_messages(connection, queue_name, now)
            row = connection.execute(
                """
                SELECT id, payload, dequeue_count
                FROM queue_messages
                WHERE queue_name = ? AND visible_at <= ?
                ORDER BY id
                LIMIT 1
                """,
                (queue_name, now),
            ).fetchone()
            if row is None:
                connection.commit()
                return None
            receipt = str(uuid.uuid4())
            dequeue_count = int(row["dequeue_count"]) + 1
            connection.execute(
                """
                UPDATE queue_messages
                SET visible_at = ?, dequeue_count = ?, receipt = ?
                WHERE id = ? AND queue_name = ?
                """,
                (
                    now + self._visibility_timeout_seconds,
                    dequeue_count,
                    receipt,
                    row["id"],
                    queue_name,
                ),
            )
            connection.commit()
        return QueueMessage(
            message_id=int(row["id"]),
            payload=json.loads(row["payload"]),
            dequeue_count=dequeue_count,
            receipt=receipt,
        )

    def complete(self, queue_name: str, message_id: int | str, receipt: str) -> None:
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM queue_messages WHERE id = ? AND queue_name = ? AND receipt = ?",
                (message_id, queue_name, receipt),
            )
        if cursor.rowcount != 1:
            raise ValueError("Message receipt is stale or invalid")

    def abandon(self, queue_name: str, message_id: int | str, receipt: str) -> None:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE queue_messages SET visible_at = ?, receipt = NULL
                WHERE id = ? AND queue_name = ? AND receipt = ?
                """,
                (self._timestamp(), message_id, queue_name, receipt),
            )
        if cursor.rowcount != 1:
            raise ValueError("Message receipt is stale or invalid")

    def _move_exhausted_messages(
        self, connection: sqlite3.Connection, queue_name: str, now: float
    ) -> None:
        poison_name = f"{queue_name}-poison"
        exhausted = connection.execute(
            """
            SELECT id, payload, created_at FROM queue_messages
            WHERE queue_name = ? AND visible_at <= ? AND dequeue_count >= ?
            """,
            (queue_name, now, self._max_dequeue_count),
        ).fetchall()
        for row in exhausted:
            connection.execute(
                """
                INSERT INTO queue_messages
                    (queue_name, payload, visible_at, dequeue_count, created_at)
                VALUES (?, ?, ?, 0, ?)
                """,
                (poison_name, row["payload"], now, row["created_at"]),
            )
            connection.execute("DELETE FROM queue_messages WHERE id = ?", (row["id"],))
