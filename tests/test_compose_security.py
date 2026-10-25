from __future__ import annotations

from pathlib import Path

import yaml


def test_all_compose_ports_bind_to_loopback() -> None:
    compose = yaml.safe_load(Path("compose.yml").read_text(encoding="utf-8"))
    published_ports = [
        port for service in compose["services"].values() for port in service.get("ports", [])
    ]

    assert published_ports
    assert all(str(port).startswith("127.0.0.1:") for port in published_ports)


def test_mailpit_exposes_loopback_only_smtp_and_web_ports() -> None:
    compose = yaml.safe_load(Path("compose.yml").read_text(encoding="utf-8"))

    assert compose["services"]["mailpit"]["ports"] == [
        "127.0.0.1:1025:1025",
        "127.0.0.1:8025:8025",
    ]
