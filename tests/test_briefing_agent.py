from __future__ import annotations

import json

import pytest

from nzhem.core.agent.briefing import (
    DraftBriefingService,
    build_briefing_facts,
    should_draft_briefing,
    validate_narrative_fidelity,
)
from nzhem.core.agent.schemas import BRIEFING_OUTPUT_SCHEMA, TOOL_SCHEMAS


def kaikoura_summary() -> dict:
    return {
        "event_id": "2016p858000",
        "name": "Kaikōura 2016",
        "origin_time": "2016-11-14T00:02:56.346000+13:00",
        "magnitude": 7.8,
        "depth_km": 15.11,
        "max_mmi": 8.4,
        "buildings_mmi_ge_6": 78564,
        "population_mmi_ge_6": 83276.4607,
        "no_damaging_shaking": False,
        "source_kind": "official",
        "as_if_today": True,
        "regions": [
            {
                "region_code": "MBH",
                "region_name": "Marlborough Region",
                "buildings": 30423,
                "population": 31464.2,
            }
        ],
    }


class FixedTools:
    def get_event(self, event_id: str) -> dict:
        return {
            "event_id": event_id,
            "magnitude": 7.8,
            "populated_max_mmi": 8.4,
            "longitude": 173.022,
            "latitude": -42.693,
        }

    def get_published_summary(self, event_id: str) -> dict:
        summary = kaikoura_summary()
        summary["event_id"] = event_id
        return summary


def narrative(text: str = "This assessment uses the official shaking layer.") -> dict:
    return {
        "situation": [
            {"text": text, "metric_refs": [], "region_refs": []},
            {
                "text": ("Marlborough Region has the largest mapped damaging-shaking exposure."),
                "metric_refs": [],
                "region_refs": ["Marlborough Region"],
            },
            {
                "text": "The results describe exposure and do not estimate damage or loss.",
                "metric_refs": [],
                "region_refs": [],
            },
        ],
        "recommended_checks": [
            {
                "text": "Review the mapped shaking footprint before operational use.",
                "metric_refs": [],
                "region_refs": [],
            }
        ],
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
        if self.calls == 1:
            invalid = narrative("The event exposed 347,821 buildings.")
            invalid["situation"][0]["metric_refs"] = ["buildings_mmi_ge_6"]
            return json.dumps(invalid)
        return json.dumps(narrative())


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


def test_four_tool_schemas_remain_closed() -> None:
    assert set(TOOL_SCHEMAS) == {
        "get_event",
        "get_exposure_summary",
        "compare_then_now",
        "get_region_context",
    }
    assert all(schema["additionalProperties"] is False for schema in TOOL_SCHEMAS.values())


def test_deterministic_template_uses_only_published_summary() -> None:
    facts = build_briefing_facts(kaikoura_summary())

    assert facts["headline"] == (
        "M7.8 Kaikōura, 14 Nov 2016 — 78,564 buildings in MMI 6+ shaking (as-if-today)"
    )
    displays = {item["label"]: item["display"] for item in facts["key_figures"]}
    assert displays["Depth"] == "15.1 km"
    assert displays["People in MMI 6+ shaking"] == "83,276"
    assert displays["Most affected region"] == (
        "Marlborough Region · 30,423 buildings · 31,464 people"
    )
    assert displays["Shaking source"] == "Official shaking layer"
    assert displays["Assessment basis"] == "As-if-today"
    assert facts["required_situation"] == (
        "Marlborough Region has the largest mapped damaging-shaking exposure."
    )


def test_no_damage_headline_is_explicit() -> None:
    summary = kaikoura_summary()
    summary.update(
        {
            "name": "Taumarunui Deep 2026",
            "origin_time": "2026-10-15T18:25:34+13:00",
            "magnitude": 5.5,
            "max_mmi": 2.8,
            "buildings_mmi_ge_6": 0,
            "population_mmi_ge_6": 0,
            "no_damaging_shaking": True,
            "regions": [],
        }
    )
    assert build_briefing_facts(summary)["headline"] == (
        "M5.5 Taumarunui Deep, 15 Oct 2026 — No damaging shaking (max MMI 2.8) (as-if-today)"
    )


def test_draft_retries_fact_boundary_violation_and_removes_then_and_now() -> None:
    llm = RetryingLlm()
    result = DraftBriefingService(
        FixedTools(), llm, max_output_tokens=450, total_token_limit=12000
    ).draft("2016p858000")

    assert result.fidelity_passed is True
    assert result.status == "pending"
    assert result.attempts == 2
    assert "78,564" in result.markdown
    assert "## Situation" in result.markdown
    assert "Then and now" not in result.markdown
    assert "get_region_context" not in result.markdown
    assert "appearance and disappearance" not in result.markdown
    assert "Marlborough Region has the largest" in result.markdown
    assert llm.schemas == [BRIEFING_OUTPUT_SCHEMA, BRIEFING_OUTPUT_SCHEMA]


def test_event_time_draft_keeps_lifecycle_limitation() -> None:
    class EventTimeTools(FixedTools):
        def get_published_summary(self, event_id: str) -> dict:
            summary = super().get_published_summary(event_id)
            summary["as_if_today"] = False
            return summary

    result = DraftBriefingService(
        EventTimeTools(), RetryingLlm(), max_output_tokens=450, total_token_limit=12000
    ).draft("2016p858000")

    assert "appearance and disappearance" in result.markdown


@pytest.mark.parametrize(
    ("text", "metric_refs", "region_refs", "marker"),
    [
        ("The event exposed 347,821 buildings.", ["buildings_mmi_ge_6"], [], "number"),
        ("Taumarunui Region was most affected.", [], ["Taumarunui Region"], "region"),
        ("The get_region_context result should be checked.", [], [], "internal_term"),
        ("Population exposure was 83,276.46 people.", ["population_mmi_ge_6"], [], "number"),
        ("The total_buildings field is authoritative.", [], [], "internal_term"),
        ("Event 2016p858000 requires review.", [], [], "event_id"),
        ("National exposure was 3,219,311 buildings.", ["buildings_mmi_ge_6"], [], "number"),
        ("Exposure was 78,564 people.", ["buildings_mmi_ge_6"], [], "number"),
    ],
)
def test_review_failures_are_blocked(
    text: str, metric_refs: list[str], region_refs: list[str], marker: str
) -> None:
    payload = narrative(text)
    payload["situation"][0]["metric_refs"] = metric_refs
    payload["situation"][0]["region_refs"] = region_refs

    invalid = validate_narrative_fidelity(payload, build_briefing_facts(kaikoura_summary()))

    assert any(marker in item for item in invalid)


def test_metric_and_value_match_accepts_a_correct_structured_reference() -> None:
    payload = narrative("Exposure includes 78,564 buildings in damaging shaking.")
    payload["situation"][0]["metric_refs"] = ["buildings_mmi_ge_6"]
    facts = build_briefing_facts(kaikoura_summary())
    facts["allowed_situation"] = (
        *facts["allowed_situation"],
        "Exposure includes 78,564 buildings in damaging shaking.",
    )

    assert validate_narrative_fidelity(payload, facts) == ()


def test_draft_attaches_server_side_static_map_when_enabled() -> None:
    maps = StaticMapRecorder()
    result = DraftBriefingService(
        FixedTools(),
        RetryingLlm(),
        max_output_tokens=450,
        total_token_limit=12000,
        static_map_provider=maps,
    ).draft("2016p858000", briefing_id="briefing-1")

    assert result.map_status == "attached"
    assert result.map_image == b"\x89PNG\r\n\x1a\nmap"
    assert maps.calls == [{"briefing_id": "briefing-1", "longitude": 173.022, "latitude": -42.693}]


def test_static_map_failure_does_not_block_briefing() -> None:
    result = DraftBriefingService(
        FixedTools(),
        RetryingLlm(),
        max_output_tokens=450,
        total_token_limit=12000,
        static_map_provider=FailingStaticMap(),
    ).draft("2016p858000", briefing_id="briefing-1")

    assert result.status == "pending"
    assert result.map_status == "failed"
    assert result.map_image is None


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
