from pathlib import Path

import pytest

from nzhem.adapters.local.sqlite import SqliteQueueStore, SqliteTableStore


def test_table_upsert_get_and_list(tmp_path: Path) -> None:
    store = SqliteTableStore(tmp_path / "state.db")
    store.upsert_entity("runs", {"PartitionKey": "housekeeping", "RowKey": "1", "value": 1})
    store.upsert_entity("runs", {"PartitionKey": "housekeeping", "RowKey": "1", "value": 2})

    assert store.get_entity("runs", "housekeeping", "1")["value"] == 2
    assert len(store.list_entities("runs", "housekeeping")) == 1
    assert store.get_entity("runs", "missing", "1") is None


def test_queue_visibility_receipts_and_completion(tmp_path: Path) -> None:
    now = [100.0]
    queue = SqliteQueueStore(
        tmp_path / "state.db",
        visibility_timeout_seconds=10,
        max_dequeue_count=3,
        timestamp=lambda: now[0],
    )
    message_id = queue.send("events", {"event_id": "one"})
    first = queue.receive("events")

    assert first is not None
    assert first.message_id == message_id
    assert first.dequeue_count == 1
    assert queue.receive("events") is None
    with pytest.raises(ValueError, match="receipt"):
        queue.complete("events", message_id, "wrong")

    now[0] = 111.0
    second = queue.receive("events")
    assert second is not None
    assert second.dequeue_count == 2
    queue.complete("events", second.message_id, second.receipt)
    assert queue.receive("events") is None


def test_queue_moves_exhausted_message_to_poison(tmp_path: Path) -> None:
    now = [100.0]
    queue = SqliteQueueStore(
        tmp_path / "state.db",
        visibility_timeout_seconds=10,
        max_dequeue_count=3,
        timestamp=lambda: now[0],
    )
    queue.send("events", {"event_id": "bad"})
    for attempt in range(3):
        message = queue.receive("events")
        assert message is not None
        assert message.dequeue_count == attempt + 1
        now[0] += 11

    assert queue.receive("events") is None
    poison = queue.receive("events-poison")
    assert poison is not None
    assert poison.payload["event_id"] == "bad"


def test_queue_abandon_makes_message_visible(tmp_path: Path) -> None:
    queue = SqliteQueueStore(tmp_path / "state.db")
    queue.send("events", {"event_id": "retry"})
    message = queue.receive("events")
    assert message is not None
    queue.abandon("events", message.message_id, message.receipt)
    assert queue.receive("events").dequeue_count == 2
