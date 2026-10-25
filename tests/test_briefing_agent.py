from __future__ import annotations

import json

from nzhem.core.agent.briefing import (
    DraftBriefingService,
    should_draft_briefing,
    validate_key_figure_provenance,
    validate_numeric_fidelity,
)
from nzhem.core.agent.schemas import BRIEFING_OUTPUT_SCHEMA, LIMITATIONS, TOOL_SCHEMAS


class FixedTools:
    def get_event(self, event_id: str) -> dict:
        return {
            "event_id": event_id,
            "magnitude": 6.0,
            "depth_km": 10.0,
            "longitude": 172.6,
            "latitude": -43.5,
        }

    def get_exposure_summary(self, event_id: str, mmi_threshold: float) -> list[dict]:
        return [
            {
                "region_code": "01",
                "region_name": "Region A",
                "buildings": 20,
                "footprint_area_m2": 100.0,
                "population_2023": 30.0,
            }
        ]

    def compare_then_now(self, event_id: str, mmi_threshold: float) -> list[dict]:
        return [
            {
                "region_code": "01",
                "region_name": "Region A",
                "then_buildings": 15,
                "now_buildings": 20,
                "change_buildings": 5,
            }
        ]

    def get_region_context(self, region_code: str) -> dict:
        return {
            "region_code": region_code,
            "total_buildings": 40,
            "population_2023": 50.0,
            "strong_event_count": 2,
        }


class RetryingLlm:
    def __init__(self) -> None:
        self.calls = 0
        self.schemas: list[dict | None] = []

    def generate(
        self, prompt: str, *, max_output_tokens: int, response_schema: dict | None = None
    ) -> str:
        self.calls += 1
        self.schemas.append(response_schema)
        value = 999 if self.calls == 1 else 20
        return json.dumps(
            {
                "headline": "Earthquake exposure briefing",
                "key_figures": [
                    {
                        "label": "Magnitude",
                        "value": 6,
                        "unit": "M",
                        "source_tool": "get_event",
                        "source_field": "magnitude",
                    },
                    {
                        "label": "Buildings",
                        "value": value,
                        "unit": "buildings",
                        "source_tool": "get_exposure_summary",
                        "source_field": "buildings",
                    },
                    {
                        "label": "Population",
                        "value": 30,
                        "unit": "people",
                        "source_tool": "get_exposure_summary",
                        "source_field": "population_2023",
                    },
                ],
                "regions_most_affected": ["Region A"],
                "then_vs_now": "The building count changed by 5.",
                "limitations": list(LIMITATIONS),
                "recommended_checks": ["Review official emergency information."],
                "generated_at": "2026-10-26T00:00:00Z",
            }
        )


class StaticMapRecorder:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def render(self, *, briefing_id: str, longitude: float, latitude: float) -> bytes:
        self.calls.append(
            {"briefing_id": briefing_id, "longitude": longitude, "latitude": latitude}
        )
        return b"\x89PNG\r\n\x1a\nmap"


class FailingStaticMap:
    def render(self, *, briefing_id: str, longitude: float, latitude: float) -> bytes:
        raise RuntimeError("provider details must not escape")


def test_four_tool_schemas_are_closed() -> None:
    assert set(TOOL_SCHEMAS) == {
        "get_event",
        "get_exposure_summary",
        "compare_then_now",
        "get_region_context",
    }
    assert all(schema["additionalProperties"] is False for schema in TOOL_SCHEMAS.values())


def test_draft_retries_unsupported_numbers_and_renders_both_formats() -> None:
    llm = RetryingLlm()
    result = DraftBriefingService(
        FixedTools(), llm, max_output_tokens=450, total_token_limit=12000
    ).draft("event-1")

    assert result.fidelity_passed is True
    assert result.status == "pending"
    assert result.attempts == 2
    assert "## Limitations" in result.markdown
    assert "<h2>Limitations</h2>" in result.html
    assert llm.schemas == [BRIEFING_OUTPUT_SCHEMA, BRIEFING_OUTPUT_SCHEMA]


def test_draft_attaches_server_side_static_map_when_enabled() -> None:
    maps = StaticMapRecorder()
    result = DraftBriefingService(
        FixedTools(),
        RetryingLlm(),
        max_output_tokens=450,
        total_token_limit=12000,
        static_map_provider=maps,
    ).draft("event-1", briefing_id="briefing-1")

    assert result.map_status == "attached"
    assert result.map_image == b"\x89PNG\r\n\x1a\nmap"
    assert maps.calls == [{"briefing_id": "briefing-1", "longitude": 172.6, "latitude": -43.5}]


def test_static_map_failure_does_not_block_briefing() -> None:
    result = DraftBriefingService(
        FixedTools(),
        RetryingLlm(),
        max_output_tokens=450,
        total_token_limit=12000,
        static_map_provider=FailingStaticMap(),
    ).draft("event-1", briefing_id="briefing-1")

    assert result.status == "pending"
    assert result.map_status == "failed"
    assert result.map_image is None


def test_fidelity_ignores_provenance_field_digits_but_checks_visible_numbers() -> None:
    payload = json.loads(RetryingLlm().generate("", max_output_tokens=450))
    payload["key_figures"][1]["source_field"] = "population_2023"
    tool_results = {
        "get_event": {"magnitude": 6.0},
        "get_exposure_summary": [{"buildings": 999, "population_2023": 30}],
        "compare_then_now": [{"change_buildings": 5}],
        "get_region_context": {},
    }

    assert validate_numeric_fidelity(payload, tool_results) == (True, ())
    payload["headline"] = "Unsupported 998"
    assert validate_numeric_fidelity(payload, tool_results) == (False, ("998",))


def test_key_figure_provenance_requires_matching_tool_field_and_value() -> None:
    payload = json.loads(RetryingLlm().generate("", max_output_tokens=450))
    tool_results = {
        "get_event": {"magnitude": 6.0},
        "get_exposure_summary": [{"buildings": 999, "population_2023": 30}],
        "compare_then_now": [],
        "get_region_context": {},
    }

    assert validate_key_figure_provenance(payload, tool_results) == ()
    payload["key_figures"][0]["value"] = 7
    assert validate_key_figure_provenance(payload, tool_results) == ("key_figures[0]",)


def test_trigger_requires_significant_event_or_material_magnitude_update() -> None:
    assert should_draft_briefing({"magnitude": 5.0, "populated_max_mmi": 4.0})
    assert should_draft_briefing({"magnitude": 4.0, "populated_max_mmi": 5.0})
    assert not should_draft_briefing({"magnitude": 4.9, "populated_max_mmi": 4.9})
    assert not should_draft_briefing(
        {"magnitude": 6.1, "populated_max_mmi": 6.0}, previous_magnitude=6.0
    )
    assert should_draft_briefing(
        {"magnitude": 6.3, "populated_max_mmi": 6.0}, previous_magnitude=6.0
    )
