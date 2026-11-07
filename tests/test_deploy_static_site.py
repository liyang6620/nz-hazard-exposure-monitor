from __future__ import annotations

import json

import pytest
from azure.core.exceptions import ResourceNotFoundError
from scripts.deploy_static_site import published_event_ids


class Blob:
    def __init__(self, data: bytes) -> None:
        self.data = data

    def download_blob(self) -> Blob:
        return self

    def readall(self) -> bytes:
        return self.data


class Web:
    def __init__(self, blobs: dict[str, bytes]) -> None:
        self.blobs = blobs

    def get_blob_client(self, path: str) -> Blob:
        if path not in self.blobs:
            raise ResourceNotFoundError("Blob not found")
        return Blob(self.blobs[path])


def test_static_deploy_refreshes_routes_from_published_generation() -> None:
    web = Web(
        {
            "data/manifest.json": json.dumps(
                {"base_path": "/data/generations/20261107T040014475547Z"}
            ).encode(),
            "data/generations/20261107T040014475547Z/events.json": json.dumps(
                [{"event_id": "2016p858000"}, {"event_id": "2026p838250"}]
            ).encode(),
        }
    )
    assert published_event_ids(web) == ["2016p858000", "2026p838250"]


def test_static_deploy_accepts_first_publish_without_manifest() -> None:
    assert published_event_ids(Web({})) == []


def test_static_deploy_rejects_unexpected_generation_path() -> None:
    web = Web({"data/manifest.json": b'{"base_path":"/data/../private"}'})
    with pytest.raises(ValueError, match="Unexpected published generation path"):
        published_event_ids(web)
