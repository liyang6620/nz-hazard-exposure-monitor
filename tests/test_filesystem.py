from pathlib import Path

import pytest

from nzhem.adapters.local.filesystem import LocalObjectStore, LocalStaticSitePublisher


def test_object_store_matches_adls_container_layout(tmp_path: Path) -> None:
    store = LocalObjectStore(tmp_path)
    store.put_bytes("gold", "events/event-1.json", b"payload")

    assert store.get_bytes("gold", "events/event-1.json") == b"payload"
    assert (tmp_path / "gold" / "events" / "event-1.json").read_bytes() == b"payload"


def test_object_store_rejects_path_traversal(tmp_path: Path) -> None:
    store = LocalObjectStore(tmp_path)
    with pytest.raises(ValueError, match="relative"):
        store.put_bytes("gold", "../secret", b"no")


def test_static_site_writes_web_container(tmp_path: Path) -> None:
    store = LocalObjectStore(tmp_path)
    LocalStaticSitePublisher(store).publish("briefings/test.html", b"briefing")
    assert store.get_bytes("web", "briefings/test.html") == b"briefing"
