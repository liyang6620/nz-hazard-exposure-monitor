from datetime import UTC, datetime
from pathlib import Path

import pytest

from nzhem.adapters.local.sqlite import SqliteTableStore
from nzhem.core.agent.esri import EsriStaticMapGuard, EsriToolRejected


def test_esri_guard_allows_only_static_maps_and_records_failure(tmp_path: Path) -> None:
    tables = SqliteTableStore(tmp_path / "state.sqlite3")
    guard = EsriStaticMapGuard(tables)
    now = datetime(2026, 10, 26, tzinfo=UTC)

    with pytest.raises(EsriToolRejected, match="Only the static map"):
        guard.reserve(tool_name="geocode", briefing_id="briefing-1", now=now)

    reservation = guard.reserve(tool_name="static_map", briefing_id="briefing-1", now=now)
    guard.record_result(reservation, success=False)
    record = tables.get_entity("runs", "esri_static_map", reservation.row_key)
    assert record["status"] == "failed"


def test_esri_guard_enforces_per_briefing_and_monthly_limits(tmp_path: Path) -> None:
    tables = SqliteTableStore(tmp_path / "state.sqlite3")
    now = datetime(2026, 10, 26, tzinfo=UTC)
    guard = EsriStaticMapGuard(tables, per_briefing_limit=2, monthly_limit=3)

    guard.reserve(tool_name="static_map", briefing_id="briefing-1", now=now)
    guard.reserve(tool_name="static_map", briefing_id="briefing-1", now=now)
    with pytest.raises(EsriToolRejected, match="Per-briefing"):
        guard.reserve(tool_name="static_map", briefing_id="briefing-1", now=now)

    guard.reserve(tool_name="static_map", briefing_id="briefing-2", now=now)
    with pytest.raises(EsriToolRejected, match="Monthly"):
        guard.reserve(tool_name="static_map", briefing_id="briefing-3", now=now)
