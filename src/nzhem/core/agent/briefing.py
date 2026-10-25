from __future__ import annotations

import html
import json
import re
from collections.abc import Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Protocol

from nzhem.core.agent.limits import BriefingLimitExceeded
from nzhem.core.agent.schemas import BRIEFING_OUTPUT_SCHEMA, LIMITATIONS
from nzhem.ports import LlmClient, StaticMapProvider

NUMBER_PATTERN = re.compile(r"(?<![A-Za-z0-9_])[-+]?\d[\d,]*(?:\.\d+)?%?")


class BriefingTools(Protocol):
    def get_event(self, event_id: str) -> Mapping[str, Any]: ...

    def get_exposure_summary(
        self, event_id: str, mmi_threshold: float
    ) -> Sequence[Mapping[str, Any]]: ...

    def compare_then_now(
        self, event_id: str, mmi_threshold: float
    ) -> Sequence[Mapping[str, Any]]: ...

    def get_region_context(self, region_code: str) -> Mapping[str, Any]: ...


@dataclass(frozen=True)
class DraftResult:
    payload: Mapping[str, Any]
    markdown: str
    html: str
    fidelity_passed: bool
    invalid_numbers: tuple[str, ...]
    attempts: int
    status: str
    map_image: bytes | None = None
    map_status: str = "not_requested"


def should_draft_briefing(
    event: Mapping[str, Any], *, previous_magnitude: float | None = None
) -> bool:
    magnitude = float(event["magnitude"])
    populated_max_mmi = float(event["populated_max_mmi"])
    if magnitude < 5.0 and populated_max_mmi < 5.0:
        return False
    return previous_magnitude is None or abs(
        Decimal(str(magnitude)) - Decimal(str(previous_magnitude))
    ) >= Decimal("0.3")


def _normalise_number(value: str | int | float | Decimal) -> Decimal:
    raw = str(value).replace(",", "").strip()
    percent = raw.endswith("%")
    if percent:
        raw = raw[:-1]
    number = Decimal(raw)
    return number / 100 if percent else number


def _source_numbers(value: Any) -> set[Decimal]:
    found: set[Decimal] = set()
    if isinstance(value, bool) or value is None:
        return found
    if isinstance(value, int | float | Decimal):
        with suppress(InvalidOperation):
            found.add(_normalise_number(value))
        return found
    if isinstance(value, str):
        for token in NUMBER_PATTERN.findall(value):
            with suppress(InvalidOperation):
                found.add(_normalise_number(token))
        return found
    if isinstance(value, Mapping):
        for nested in value.values():
            found.update(_source_numbers(nested))
        return found
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        for nested in value:
            found.update(_source_numbers(nested))
    return found


def validate_numeric_fidelity(
    payload: Mapping[str, Any], tool_results: Mapping[str, Any]
) -> tuple[bool, tuple[str, ...]]:
    allowed = _source_numbers(tool_results)
    content = {
        "headline": payload.get("headline"),
        "key_figures": [
            {
                "label": item.get("label"),
                "value": item.get("value"),
                "unit": item.get("unit"),
            }
            for item in payload.get("key_figures", [])
        ],
        "regions_most_affected": payload.get("regions_most_affected"),
        "then_vs_now": payload.get("then_vs_now"),
        "limitations": payload.get("limitations"),
        "recommended_checks": payload.get("recommended_checks"),
    }
    invalid: set[str] = set()
    for token in NUMBER_PATTERN.findall(json.dumps(content, ensure_ascii=True)):
        try:
            number = _normalise_number(token)
        except InvalidOperation:
            continue
        if number not in allowed:
            invalid.add(token)
    return not invalid, tuple(sorted(invalid))


def validate_briefing_payload(payload: Mapping[str, Any]) -> None:
    required = set(BRIEFING_OUTPUT_SCHEMA["required"])
    if set(payload) != required:
        raise ValueError("Briefing output fields do not match the strict schema")
    if tuple(payload["limitations"]) != LIMITATIONS:
        raise ValueError("Briefing limitations do not match the required text")
    if len(payload["key_figures"]) < 3:
        raise ValueError("At least three key figures are required")


def validate_key_figure_provenance(
    payload: Mapping[str, Any], tool_results: Mapping[str, Any]
) -> tuple[str, ...]:
    def field_values(value: Any, field: str) -> list[Any]:
        found: list[Any] = []
        if isinstance(value, Mapping):
            if field in value:
                found.append(value[field])
            for nested in value.values():
                found.extend(field_values(nested, field))
        elif isinstance(value, Sequence) and not isinstance(value, str | bytes):
            for nested in value:
                found.extend(field_values(nested, field))
        return found

    invalid: list[str] = []
    for index, figure in enumerate(payload["key_figures"]):
        source = tool_results.get(figure["source_tool"])
        matches = False
        for value in field_values(source, figure["source_field"]):
            with suppress(InvalidOperation):
                if _normalise_number(value) == _normalise_number(figure["value"]):
                    matches = True
                    break
        if not matches:
            invalid.append(f"key_figures[{index}]")
    return tuple(invalid)


def _display_number(value: Any) -> str:
    number = Decimal(str(value))
    if number == number.to_integral_value():
        return f"{int(number):,}"
    return f"{number:,.2f}".rstrip("0").rstrip(".")


def render_markdown(payload: Mapping[str, Any]) -> str:
    figures = "\n".join(
        f"- **{item['label']}:** {_display_number(item['value'])} {item['unit']}"
        for item in payload["key_figures"]
    )
    regions = "\n".join(f"- {value}" for value in payload["regions_most_affected"])
    limitations = "\n".join(f"- {value}" for value in payload["limitations"])
    checks = "\n".join(f"- {value}" for value in payload["recommended_checks"])
    return (
        f"# {payload['headline']}\n\n## Key figures\n\n{figures}\n\n"
        f"## Regions most affected\n\n{regions}\n\n## Then and now\n\n"
        f"{payload['then_vs_now']}\n\n## Limitations\n\n{limitations}\n\n"
        f"## Recommended checks\n\n{checks}\n\n"
        "Detailed analysis: see the Power BI report demonstration in the repository README.\n"
    )


def render_html(payload: Mapping[str, Any]) -> str:
    def items(values: Sequence[str]) -> str:
        return "".join(f"<li>{html.escape(str(value))}</li>" for value in values)

    figures = "".join(
        "<li><strong>"
        + html.escape(str(item["label"]))
        + ":</strong> "
        + html.escape(f"{_display_number(item['value'])} {item['unit']}")
        + "</li>"
        for item in payload["key_figures"]
    )
    return (
        "<!doctype html><html lang='en'><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{html.escape(str(payload['headline']))}</title><main>"
        f"<h1>{html.escape(str(payload['headline']))}</h1>"
        f"<h2>Key figures</h2><ul>{figures}</ul>"
        f"<h2>Regions most affected</h2><ul>{items(payload['regions_most_affected'])}</ul>"
        f"<h2>Then and now</h2><p>{html.escape(str(payload['then_vs_now']))}</p>"
        f"<h2>Limitations</h2><ul>{items(payload['limitations'])}</ul>"
        f"<h2>Recommended checks</h2><ul>{items(payload['recommended_checks'])}</ul>"
        "<p>Detailed analysis: see the Power BI report demonstration in the repository README.</p>"
        "</main></html>"
    )


class DraftBriefingService:
    def __init__(
        self,
        tools: BriefingTools,
        llm: LlmClient,
        *,
        max_output_tokens: int,
        total_token_limit: int,
        static_map_provider: StaticMapProvider | None = None,
    ) -> None:
        self._tools = tools
        self._llm = llm
        self._max_output_tokens = max_output_tokens
        self._total_token_limit = total_token_limit
        self._static_map_provider = static_map_provider

    def draft(
        self,
        event_id: str,
        *,
        mmi_threshold: float = 6.0,
        briefing_id: str | None = None,
    ) -> DraftResult:
        event = dict(self._tools.get_event(event_id))
        exposure = [dict(row) for row in self._tools.get_exposure_summary(event_id, mmi_threshold)]
        comparison = [dict(row) for row in self._tools.compare_then_now(event_id, mmi_threshold)]
        region_context = {
            row["region_code"]: dict(self._tools.get_region_context(row["region_code"]))
            for row in exposure[:3]
            if row["region_code"] != "unknown"
        }
        tool_results = {
            "get_event": event,
            "get_exposure_summary": exposure,
            "compare_then_now": comparison,
            "get_region_context": region_context,
            "parameters": {"mmi_threshold": mmi_threshold},
        }
        prompt = (
            "Create a concise NZ earthquake exposure briefing as strict JSON. "
            "Use only numbers present in TOOL_RESULTS. Do not number lists. "
            "Return 3 to 5 key figures, no more than 3 affected regions, and no more "
            "than 3 recommended checks. Keep every text item to one short sentence. "
            "For every key figure, source_tool and source_field must identify a tool "
            "result field whose numeric value exactly matches the figure value. "
            "Copy the three REQUIRED_LIMITATIONS exactly and in order.\n"
            f"REQUIRED_LIMITATIONS={json.dumps(LIMITATIONS)}\n"
            f"TOOL_RESULTS={json.dumps(tool_results, default=str, separators=(',', ':'))}"
        )
        payload: Mapping[str, Any] = {}
        invalid: tuple[str, ...] = ()
        attempts = 0
        estimated_tokens = 0
        valid_payload_received = False
        for _ in range(3):
            call_tokens = (len(prompt) + 3) // 4 + self._max_output_tokens
            if estimated_tokens + call_tokens > self._total_token_limit:
                raise BriefingLimitExceeded("per-briefing token limit reached before model call")
            estimated_tokens += call_tokens
            attempts += 1
            output = self._llm.generate(
                prompt,
                max_output_tokens=self._max_output_tokens,
                response_schema=BRIEFING_OUTPUT_SCHEMA,
            )
            try:
                payload = json.loads(output)
                validate_briefing_payload(payload)
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                invalid = ("invalid_json_or_schema",)
                prompt += (
                    "\nThe previous response was incomplete or did not match the schema. "
                    "Return a shorter, complete JSON response."
                )
                continue
            valid_payload_received = True
            passed, invalid_numbers = validate_numeric_fidelity(payload, tool_results)
            invalid_provenance = validate_key_figure_provenance(payload, tool_results)
            invalid = (*invalid_numbers, *invalid_provenance)
            passed = passed and not invalid_provenance
            if passed:
                break
            prompt += (
                "\nThe previous response contained unsupported numbers: "
                + ", ".join(invalid)
                + ". Regenerate without them."
            )
        if not valid_payload_received:
            raise ValueError("Model did not return a complete briefing payload")
        status = "pending" if not invalid else "needs_manual_review"
        map_image: bytes | None = None
        map_status = "not_requested"
        if self._static_map_provider is not None and briefing_id is not None:
            map_status = "failed"
            try:
                map_image = self._static_map_provider.render(
                    briefing_id=briefing_id,
                    longitude=float(event["longitude"]),
                    latitude=float(event["latitude"]),
                )
                map_status = "attached"
            except Exception:
                # A failed optional map must not prevent a briefing from going
                # through the existing approval workflow.  The adapter records
                # the failed, quota-counted attempt without exposing details.
                map_image = None
        return DraftResult(
            payload=payload,
            markdown=render_markdown(payload),
            html=render_html(payload),
            fidelity_passed=not invalid,
            invalid_numbers=invalid,
            attempts=attempts,
            status=status,
            map_image=map_image,
            map_status=map_status,
        )
