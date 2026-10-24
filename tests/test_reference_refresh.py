from __future__ import annotations

import gzip
import io
import json
from pathlib import Path
from unittest.mock import Mock

import pytest
import requests

from nzhem.adapters.local import resource_guard as guard_module
from nzhem.adapters.local.resource_guard import ResourceGuard, ResourceLimitExceeded
from nzhem.adapters.local.wfs import (
    WfsError,
    WfsPageDownloader,
    WfsPartition,
    WfsSource,
)
from nzhem.config import ConfigurationError, Settings
from nzhem.core.reference import RefreshReferenceService
from nzhem.ports import ReferenceRefreshResult


class FakeRaw(io.BytesIO):
    decode_content = False


class FakeResponse:
    def __init__(self, body: bytes, status_code: int = 200) -> None:
        self.content = body
        self.raw = FakeRaw(body)
        self.status_code = status_code
        self.closed = False

    def close(self) -> None:
        self.closed = True


class FakeSession:
    def __init__(self, responses: list[FakeResponse | Exception]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, dict[str, object]]] = []

    def get(self, endpoint: str, **kwargs: object) -> FakeResponse:
        self.calls.append((endpoint, kwargs))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class FakeSecrets:
    def get_secret(self, name: str) -> str:
        assert name == "TEST_API_KEY"
        return "never-log-this-value"


SOURCE = WfsSource(
    name="test_source",
    base_url="https://example.invalid",
    layer="42",
    key_name="TEST_API_KEY",
    id_field="record_id",
    geometry_field="shape",
    properties=("record_id",),
)


def _hits(count: int) -> FakeResponse:
    return FakeResponse(
        f'<wfs:FeatureCollection xmlns:wfs="urn:wfs" numberMatched="{count}"/>'.encode()
    )


def _features(*identifiers: int) -> FakeResponse:
    payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"record_id": identifier},
                "geometry": {"type": "Point", "coordinates": [174.0, -41.0]},
            }
            for identifier in identifiers
        ],
    }
    return FakeResponse(json.dumps(payload, separators=(",", ":")).encode())


def test_wfs_download_is_paged_resumable_and_has_no_key_in_manifest(tmp_path: Path) -> None:
    session = FakeSession([_hits(3), _features(1, 2), _features(3), _hits(3)])
    guard = ResourceGuard(tmp_path, min_free_disk_gb=0.0001, max_rss_mb=4096)
    downloader = WfsPageDownloader(FakeSecrets(), tmp_path, guard, page_size=2, session=session)

    pages = downloader.download(SOURCE, WfsPartition("small", (1.0, 2.0, 3.0, 4.0)))

    assert [page.expected_count for page in pages] == [2, 1]
    assert all(len(page.sha256) == 64 for page in pages)
    with gzip.open(tmp_path / pages[0].path, "rt", encoding="utf-8") as source:
        assert len(json.load(source)["features"]) == 2
    manifest = (tmp_path / "test_source" / "small" / "manifest.json").read_text()
    assert "never-log-this-value" not in manifest
    page_call = session.calls[1]
    assert page_call[1]["params"]["count"] == 2
    assert page_call[1]["params"]["sortBy"] == "record_id"
    assert page_call[1]["params"]["bbox"] == "1.0,2.0,3.0,4.0,EPSG:4326"

    resumed = FakeSession([_hits(3), _hits(3)])
    resumed_pages = WfsPageDownloader(
        FakeSecrets(), tmp_path, guard, page_size=2, session=resumed
    ).download(SOURCE, WfsPartition("small", (1.0, 2.0, 3.0, 4.0)))
    assert resumed_pages == pages
    assert len(resumed.calls) == 2


def test_wfs_retries_with_sanitized_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("nzhem.adapters.local.wfs.time.sleep", Mock())
    session = FakeSession(
        [requests.ConnectionError("secret-bearing upstream detail"), FakeResponse(b"bad", 403)]
    )
    downloader = WfsPageDownloader(
        FakeSecrets(),
        tmp_path,
        ResourceGuard(tmp_path, min_free_disk_gb=0.0001, max_rss_mb=4096),
        max_attempts=2,
        session=session,
    )

    with pytest.raises(WfsError) as error:
        downloader.count(SOURCE, WfsPartition("nationwide"))

    assert "never-log-this-value" not in str(error.value)
    assert "secret-bearing" not in str(error.value)


def test_wfs_detects_source_change_during_download(tmp_path: Path) -> None:
    session = FakeSession([_hits(1), _features(1), _hits(2)])
    downloader = WfsPageDownloader(
        FakeSecrets(),
        tmp_path,
        ResourceGuard(tmp_path, min_free_disk_gb=0.0001, max_rss_mb=4096),
        session=session,
    )
    with pytest.raises(WfsError, match="changed during paging"):
        downloader.download(SOURCE, WfsPartition("nationwide"))


def test_resource_guard_stops_before_disk_or_memory_exhaustion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    disk = Mock(return_value=Mock(free=19 * 1024**3))
    monkeypatch.setattr(guard_module.shutil, "disk_usage", disk)
    monkeypatch.setattr(guard_module, "_rss_bytes", Mock(return_value=100 * 1024**2))
    guard = ResourceGuard(tmp_path, min_free_disk_gb=20, max_rss_mb=768)
    with pytest.raises(ResourceLimitExceeded, match="Free disk"):
        guard.check()

    disk.return_value.free = 30 * 1024**3
    monkeypatch.setattr(guard_module, "_rss_bytes", Mock(return_value=800 * 1024**2))
    with pytest.raises(ResourceLimitExceeded, match="Process RSS"):
        guard.check()

    disk.return_value.free = 26 * 1024**3
    monkeypatch.setattr(guard_module, "_rss_bytes", Mock(return_value=100 * 1024**2))
    with pytest.raises(ResourceLimitExceeded, match="projected free disk"):
        guard.check(required_free_bytes=7 * 1024**3)


def test_refresh_service_delegates_and_settings_enforce_safe_caps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = ReferenceRefreshResult(1, 1, 2, 2.0, 0, 0, 1.0, 10.0, 50.0, {})
    refresher = Mock()
    refresher.refresh.return_value = result
    assert RefreshReferenceService(refresher).run() == result

    monkeypatch.setenv("REFERENCE_MIN_FREE_DISK_GB", "19")
    with pytest.raises(ConfigurationError, match="cannot be below 20"):
        Settings.from_env()

    monkeypatch.setenv("REFERENCE_MIN_FREE_DISK_GB", "20")
    monkeypatch.setenv("REFERENCE_PAGE_SIZE", "1001")
    with pytest.raises(ConfigurationError, match="safe limit"):
        Settings.from_env()
