from pathlib import Path

from nzhem.config import Settings
from nzhem.container import build_container


def test_local_container_builds_all_ports(tmp_path: Path) -> None:
    settings = Settings(
        environment="local",
        data_root=tmp_path / "data",
        sqlite_path=tmp_path / "state" / "nzhem.db",
        geonet_poll_enabled=False,
    )

    container = build_container(settings)

    assert container.settings.environment == "local"
    assert container.objects.get_bytes("web", "index.html").startswith(b"<!doctype html>")
    assert b"NZHEM event map" in container.objects.get_bytes("web", "map/index.html")
    assert container.objects.get_bytes("web", "map/data/events.json").startswith(b"[")
    result = container.housekeeping().run()
    assert result.events_enqueued == 0


def test_local_container_preserves_a_published_homepage(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    published = data_root / "web" / "index.html"
    published.parent.mkdir(parents=True)
    published.write_bytes(b"approved briefing index")
    settings = Settings(
        environment="local",
        data_root=data_root,
        sqlite_path=tmp_path / "state" / "nzhem.db",
        geonet_poll_enabled=False,
    )

    container = build_container(settings)

    assert container.objects.get_bytes("web", "index.html") == b"approved briefing index"
    assert b"NZHEM event map" in container.objects.get_bytes("web", "map/index.html")
