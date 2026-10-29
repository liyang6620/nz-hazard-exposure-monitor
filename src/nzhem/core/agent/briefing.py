from __future__ import annotations

import html
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any, Protocol
from zoneinfo import ZoneInfo

from nzhem.core.agent.limits import BriefingLimitExceeded
from nzhem.core.agent.schemas import BRIEFING_METRICS, BRIEFING_OUTPUT_SCHEMA, LIMITATIONS
from nzhem.ports import LlmClient, StaticMapProvider

NUMBER_PATTERN = re.compile(r"(?<![A-Za-z0-9_])[-+]?\d[\d,]*(?:\.\d+)?%?")
REGION_PATTERN = re.compile(
    r"\b([A-ZĀĒĪŌŪ][\wĀĒĪŌŪāēīōū'’-]*(?:\s+[A-ZĀĒĪŌŪ][\wĀĒĪŌŪāēīōū'’-]*){0,3}\s+[Rr]egion)\b"
)
INTERNAL_TERM_PATTERN = re.compile(
    r"\b(?:get_event|get_exposure_summary|get_region_context|compare_then_now|"
    r"population_2023|validation_station_count|total_buildings|event_id|"
    r"as_if_today_buildings|populated_max_mmi|source_tool|source_field|count)\b",
    re.IGNORECASE,
)
SNAKE_CASE_PATTERN = re.compile(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b")


class BriefingTools(Protocol):
    def get_event(self, event_id: str) -> Mapping[str, Any]: ...

    def get_published_summary(self, event_id: str) -> Mapping[str, Any]: ...


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
    if raw.endswith("%"):
        return Decimal(raw[:-1]) / 100
    return Decimal(raw)


def _whole_number(value: Any) -> int:
    return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _event_place(name: str) -> str:
    return re.sub(r"\s+\d{4}$", "", name).strip()


def _event_time(value: str) -> tuple[str, str]:
    local = datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(
        ZoneInfo("Pacific/Auckland")
    )
    date = f"{local.day} {local.strftime('%b %Y')}"
    return date, f"{date}, {local.strftime('%H:%M %Z')}"


def build_briefing_facts(summary: Mapping[str, Any]) -> dict[str, Any]:
    """Build every publishable fact deterministically from one summary.json."""

    place = _event_place(str(summary["name"]))
    event_date, event_time = _event_time(str(summary["origin_time"]))
    magnitude = Decimal(str(summary["magnitude"])).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    depth = Decimal(str(summary["depth_km"])).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    max_mmi = Decimal(str(summary["max_mmi"])).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    buildings = int(summary["buildings_mmi_ge_6"])
    population = _whole_number(summary["population_mmi_ge_6"])
    regions = [
        dict(region)
        for region in summary.get("regions", [])
        if int(region.get("buildings", 0)) > 0 or float(region.get("population", 0)) > 0
    ]
    top_region = regions[0] if regions else None
    no_damage = bool(summary["no_damaging_shaking"])
    suffix = " (as-if-today)" if summary.get("as_if_today") else ""
    if no_damage:
        headline = (
            f"M{magnitude:.1f} {place}, {event_date} — "
            f"No damaging shaking (max MMI {max_mmi:.1f}){suffix}"
        )
    else:
        headline = (
            f"M{magnitude:.1f} {place}, {event_date} — {buildings:,} buildings "
            f"in MMI 6+ shaking{suffix}"
        )

    metric_values: dict[str, Decimal] = {
        "magnitude": magnitude,
        "depth_km": depth,
        "max_mmi": max_mmi,
        "buildings_mmi_ge_6": Decimal(buildings),
        "population_mmi_ge_6": Decimal(population),
    }
    key_figures = [
        {"metric": "magnitude", "label": "Magnitude", "display": f"M{magnitude:.1f}"},
        {"metric": "depth_km", "label": "Depth", "display": f"{depth:.1f} km"},
        {"metric": "origin_time", "label": "Origin time", "display": event_time},
        {"metric": "max_mmi", "label": "Maximum MMI", "display": f"{max_mmi:.1f}"},
        {
            "metric": "buildings_mmi_ge_6",
            "label": "Buildings in MMI 6+ shaking",
            "display": f"{buildings:,}",
        },
        {
            "metric": "population_mmi_ge_6",
            "label": "People in MMI 6+ shaking",
            "display": f"{population:,}",
        },
    ]
    if top_region is not None:
        top_buildings = int(top_region["buildings"])
        top_population = _whole_number(top_region["population"])
        metric_values["top_region_buildings_mmi_ge_6"] = Decimal(top_buildings)
        metric_values["top_region_population_mmi_ge_6"] = Decimal(top_population)
        key_figures.append(
            {
                "metric": "top_region_mmi_ge_6",
                "label": "Most affected region",
                "display": (
                    f"{top_region['region_name']} · {top_buildings:,} buildings · "
                    f"{top_population:,} people"
                ),
            }
        )
    source_label = (
        "Official shaking layer"
        if str(summary["source_kind"]) == "official"
        else "Preliminary estimate"
    )
    key_figures.extend(
        [
            {"metric": "shaking_source", "label": "Shaking source", "display": source_label},
            {
                "metric": "assessment_basis",
                "label": "Assessment basis",
                "display": "As-if-today" if summary.get("as_if_today") else "Event time",
            },
        ]
    )
    source_sentence = f"This assessment uses the {source_label.lower()}."
    shaking_sentence = (
        "It indicates no damaging shaking in populated exposure cells."
        if no_damage
        else "It indicates damaging shaking in populated exposure cells."
    )
    basis_sentence = (
        "It applies current building stock and census population."
        if summary.get("as_if_today")
        else "It applies the supported event-time exposure basis."
    )
    return {
        "event_id": str(summary["event_id"]),
        "place": place,
        "headline": headline,
        "key_figures": key_figures,
        "metric_values": metric_values,
        "allowed_regions": tuple(str(region["region_name"]) for region in regions),
        "no_damaging_shaking": no_damage,
        "source_label": source_label,
        "as_if_today": bool(summary.get("as_if_today")),
        "allowed_situation": (
            source_sentence,
            shaking_sentence,
            basis_sentence,
            "The results describe exposure and do not estimate damage or loss.",
        ),
        "allowed_checks": (
            "Review the mapped shaking footprint before operational use.",
            "Check for updates to the authoritative shaking source.",
            "Verify the exposure totals against the published event summary.",
        ),
    }


def validate_briefing_payload(payload: Mapping[str, Any]) -> None:
    if set(payload) != set(BRIEFING_OUTPUT_SCHEMA["required"]):
        raise ValueError("Briefing output fields do not match the strict schema")
    if not 2 <= len(payload["situation"]) <= 4:
        raise ValueError("Situation must contain two to four sentences")
    if not 1 <= len(payload["recommended_checks"]) <= 3:
        raise ValueError("Recommended checks must contain one to three items")
    for item in [*payload["situation"], *payload["recommended_checks"]]:
        if set(item) != {"text", "metric_refs", "region_refs"} or not str(item["text"]).strip():
            raise ValueError("Narrative items do not match the strict schema")


def validate_narrative_fidelity(
    payload: Mapping[str, Any], facts: Mapping[str, Any]
) -> tuple[str, ...]:
    invalid: set[str] = set()
    allowed_metrics: Mapping[str, Decimal] = facts["metric_values"]
    allowed_regions = set(facts["allowed_regions"])
    event_id = str(facts["event_id"])
    for section in ("situation", "recommended_checks"):
        for index, item in enumerate(payload.get(section, [])):
            path = f"{section}[{index}]"
            text = str(item.get("text", ""))
            metric_refs = list(item.get("metric_refs", []))
            region_refs = list(item.get("region_refs", []))
            if INTERNAL_TERM_PATTERN.search(text) or SNAKE_CASE_PATTERN.search(text):
                invalid.add(f"{path}:internal_term")
            if event_id and event_id in text:
                invalid.add(f"{path}:event_id")
            allowed_text = set(
                facts["allowed_situation"] if section == "situation" else facts["allowed_checks"]
            )
            if text not in allowed_text:
                invalid.add(f"{path}:unsupported_text")

            matched_refs: set[str] = set()
            for match in NUMBER_PATTERN.finditer(text):
                token = match.group(0)
                try:
                    number = _normalise_number(token)
                except InvalidOperation:
                    invalid.add(f"{path}:number:{token}")
                    continue
                matches = [
                    metric
                    for metric in metric_refs
                    if metric in allowed_metrics
                    and allowed_metrics[metric] == number
                    and _metric_context_matches(metric, text, match.start(), match.end())
                ]
                if not matches:
                    invalid.add(f"{path}:number:{token}")
                matched_refs.update(matches)
            for metric in metric_refs:
                if metric not in BRIEFING_METRICS or metric not in allowed_metrics:
                    invalid.add(f"{path}:metric:{metric}")
                elif metric not in matched_refs:
                    invalid.add(f"{path}:unused_metric:{metric}")

            for region in region_refs:
                if region not in allowed_regions or region not in text:
                    invalid.add(f"{path}:region:{region}")
            for region_phrase in REGION_PATTERN.findall(text):
                if region_phrase not in allowed_regions:
                    invalid.add(f"{path}:region:{region_phrase}")
    return tuple(sorted(invalid))


def _metric_context_matches(metric: str, text: str, start: int, end: int) -> bool:
    context = text[max(0, start - 36) : min(len(text), end + 36)].lower()
    if metric == "magnitude":
        return "magnitude" in context or text[max(0, start - 1) : start].lower() == "m"
    if metric == "depth_km":
        return "depth" in context or "km" in context
    if metric == "max_mmi":
        return "mmi" in context and ("max" in context or "maximum" in context)
    if metric in {"buildings_mmi_ge_6", "top_region_buildings_mmi_ge_6"}:
        return "building" in context
    if metric in {"population_mmi_ge_6", "top_region_population_mmi_ge_6"}:
        return "people" in context or "population" in context
    return False


def validate_numeric_fidelity(
    payload: Mapping[str, Any], facts: Mapping[str, Any]
) -> tuple[bool, tuple[str, ...]]:
    invalid = validate_narrative_fidelity(payload, facts)
    return not invalid, invalid


def render_markdown(payload: Mapping[str, Any]) -> str:
    figures = "\n".join(
        f"- **{item['label']}:** {item['display']}" for item in payload["key_figures"]
    )
    situation = " ".join(str(item["text"]) for item in payload["situation"])
    limitations = "\n".join(f"- {value}" for value in payload["limitations"])
    checks = "\n".join(f"- {item['text']}" for item in payload["recommended_checks"])
    return (
        f"# {payload['headline']}\n\n## Key figures\n\n{figures}\n\n"
        f"## Situation\n\n{situation}\n\n## Limitations\n\n{limitations}\n\n"
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
        + html.escape(str(item["display"]))
        + "</li>"
        for item in payload["key_figures"]
    )
    situation = " ".join(str(item["text"]) for item in payload["situation"])
    checks = [str(item["text"]) for item in payload["recommended_checks"]]
    return (
        "<!doctype html><html lang='en'><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{html.escape(str(payload['headline']))}</title><main>"
        f"<h1>{html.escape(str(payload['headline']))}</h1>"
        f"<h2>Key figures</h2><ul>{figures}</ul>"
        f"<h2>Situation</h2><p>{html.escape(situation)}</p>"
        f"<h2>Limitations</h2><ul>{items(payload['limitations'])}</ul>"
        f"<h2>Recommended checks</h2><ul>{items(checks)}</ul>"
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
        del mmi_threshold
        event = dict(self._tools.get_event(event_id))
        facts = build_briefing_facts(self._tools.get_published_summary(event_id))
        prompt_facts = {
            "headline": facts["headline"],
            "no_damaging_shaking": facts["no_damaging_shaking"],
            "shaking_source": facts["source_label"],
            "assessment_basis": "as-if-today" if facts["as_if_today"] else "event time",
            "allowed_regions": facts["allowed_regions"],
        }
        prompt = (
            "Write a concise New Zealand earthquake exposure briefing as strict JSON. "
            "Write two to four short situation sentences and one to three recommended checks. "
            "The deterministic template already presents every figure, date, location and source. "
            "Select and copy sentences exactly from ALLOWED_SITUATION_SENTENCES and checks exactly "
            "from ALLOWED_RECOMMENDED_CHECKS. Do not add or paraphrase text. Use metric_refs and "
            "region_refs as empty arrays. "
            "TEMPLATE_CONTEXT="
            + json.dumps(prompt_facts, ensure_ascii=False, separators=(",", ":"))
            + "\nALLOWED_SITUATION_SENTENCES="
            + json.dumps(facts["allowed_situation"], ensure_ascii=False)
            + "\nALLOWED_RECOMMENDED_CHECKS="
            + json.dumps(facts["allowed_checks"], ensure_ascii=False)
        )
        narrative: Mapping[str, Any] = {}
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
                narrative = json.loads(output)
                validate_briefing_payload(narrative)
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                invalid = ("invalid_json_or_schema",)
                prompt += "\nThe previous response was invalid. Return shorter complete JSON."
                continue
            valid_payload_received = True
            invalid = validate_narrative_fidelity(narrative, facts)
            if not invalid:
                break
            prompt += (
                "\nThe previous narrative violated deterministic fact boundaries. "
                "Copy only the supplied allowed sentences without paraphrasing."
            )
        if not valid_payload_received:
            raise ValueError("Model did not return a complete briefing payload")

        payload = {
            "headline": facts["headline"],
            "key_figures": facts["key_figures"],
            "situation": narrative["situation"],
            "limitations": list(LIMITATIONS),
            "recommended_checks": narrative["recommended_checks"],
        }
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
