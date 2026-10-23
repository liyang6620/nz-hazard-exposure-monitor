from pathlib import Path

from scripts.e2e_replay import canonical_csv_hash, replay_and_hash

FIXTURE_ROOT = Path("tests/fixtures/e2e")


def test_replay_framework_hashes_both_required_events() -> None:
    result = replay_and_hash(FIXTURE_ROOT / "gold", FIXTURE_ROOT / "manifest.json")

    assert result["fixture_kind"] == "synthetic-m1-contract-only"
    assert set(result["events"]) == {"christchurch_2011", "kaikoura_2016"}
    for event in result["events"].values():
        assert len(event["tables"]["mart_event_summary"]) == 64


def test_hash_is_independent_of_csv_row_order(tmp_path: Path) -> None:
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"
    header = "event_id,id,value\n"
    first.write_text(header + "event,2,1.0000001\nevent,1,2\n", encoding="utf-8")
    second.write_text(header + "event,1,2.0\nevent,2,1\n", encoding="utf-8")

    first_hash = canonical_csv_hash(
        first, primary_key=["event_id", "id"], event_id="event", float_precision=6
    )
    second_hash = canonical_csv_hash(
        second, primary_key=["event_id", "id"], event_id="event", float_precision=6
    )

    assert first_hash == second_hash
