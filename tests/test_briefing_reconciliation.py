from pathlib import Path

from scripts.write_briefing_reconciliation import build_table


def test_reconciliation_uses_current_published_summaries() -> None:
    root = Path(__file__).resolve().parents[1]
    table = build_table(root / "frontend/public")

    assert "Kaikōura 2016" in table
    assert "78,564" in table
    assert "Eketāhuna 2014" in table
    assert "3,219,311" not in table
    assert "get_region_context" not in table
