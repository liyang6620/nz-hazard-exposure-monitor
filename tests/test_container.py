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
    result = container.housekeeping().run()
    assert result.events_enqueued == 0
