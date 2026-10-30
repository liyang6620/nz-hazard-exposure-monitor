from pathlib import Path

from nzhem.config import Settings
from nzhem.container import build_container


def test_local_container_builds_all_ports(tmp_path: Path) -> None:
    settings = Settings(
        environment="local",
        data_root=tmp_path / "data",
        sqlite_path=tmp_path / "state" / "nzhem.db",
        site_assets_root=Path("hosts/local/site"),
        geonet_poll_enabled=False,
    )

    container = build_container(settings)

    assert container.settings.environment == "local"
    assert container.objects.get_bytes("web", "index.html").startswith(b"<!doctype html>")
    assert b"NZHEM event map" in container.objects.get_bytes("web", "map/index.html")
    assert container.objects.get_bytes("web", "map/data/events.json").startswith(b"[")
    result = container.housekeeping().run()
    assert result.events_enqueued == 0


def test_local_container_updates_ui_assets_but_preserves_runtime_data(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    published = data_root / "web" / "index.html"
    published.parent.mkdir(parents=True)
    published.write_bytes(b"old user interface")
    runtime_data = data_root / "web" / "data" / "manifest.json"
    runtime_data.parent.mkdir(parents=True)
    runtime_data.write_bytes(b"runtime manifest")
    assets = tmp_path / "assets"
    (assets / "data").mkdir(parents=True)
    (assets / "briefings").mkdir(parents=True)
    (assets / "index.html").write_bytes(b"new user interface")
    (assets / "data" / "manifest.json").write_bytes(b"image seed manifest")
    (assets / "data" / "events.json").write_bytes(b"image seed events")
    (assets / "briefings" / "approved.html").write_bytes(b"approved seed")
    settings = Settings(
        environment="local",
        data_root=data_root,
        sqlite_path=tmp_path / "state" / "nzhem.db",
        site_assets_root=assets,
        geonet_poll_enabled=False,
    )

    container = build_container(settings)

    assert container.objects.get_bytes("web", "index.html") == b"new user interface"
    assert container.objects.get_bytes("web", "data/manifest.json") == b"runtime manifest"
    assert container.objects.get_bytes("web", "data/events.json") == b"image seed events"
    assert container.objects.get_bytes("web", "briefings/approved.html") == b"approved seed"


def test_local_container_preserves_runtime_approved_briefing(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    published = data_root / "web" / "briefings" / "approved.html"
    published.parent.mkdir(parents=True)
    published.write_bytes(b"runtime-approved briefing")
    assets = tmp_path / "assets"
    (assets / "briefings").mkdir(parents=True)
    (assets / "index.html").write_bytes(b"user interface")
    (assets / "briefings" / "approved.html").write_bytes(b"image seed briefing")
    settings = Settings(
        environment="local",
        data_root=data_root,
        sqlite_path=tmp_path / "state" / "nzhem.db",
        site_assets_root=assets,
        geonet_poll_enabled=False,
    )

    container = build_container(settings)

    assert (
        container.objects.get_bytes("web", "briefings/approved.html")
        == b"runtime-approved briefing"
    )
