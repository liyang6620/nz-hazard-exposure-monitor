from __future__ import annotations

LIMITATIONS = (
    "No policy data is used; buildings and population are exposure proxies only.",
    "Shaking layers describe modelled or observed intensity, not loss or damage.",
    "Building appearance and disappearance dates are approximate where source history "
    "is incomplete.",
)

TOOL_SCHEMAS = {
    "get_event": {
        "type": "object",
        "properties": {"event_id": {"type": "string"}},
        "required": ["event_id"],
        "additionalProperties": False,
    },
    "get_exposure_summary": {
        "type": "object",
        "properties": {
            "event_id": {"type": "string"},
            "mmi_threshold": {"type": "number", "minimum": 0, "maximum": 12},
        },
        "required": ["event_id", "mmi_threshold"],
        "additionalProperties": False,
    },
    "compare_then_now": {
        "type": "object",
        "properties": {
            "event_id": {"type": "string"},
            "mmi_threshold": {"type": "number", "minimum": 0, "maximum": 12},
        },
        "required": ["event_id", "mmi_threshold"],
        "additionalProperties": False,
    },
    "get_region_context": {
        "type": "object",
        "properties": {"region_code": {"type": "string"}},
        "required": ["region_code"],
        "additionalProperties": False,
    },
}

BRIEFING_METRICS = (
    "magnitude",
    "depth_km",
    "max_mmi",
    "buildings_mmi_ge_6",
    "population_mmi_ge_6",
    "top_region_buildings_mmi_ge_6",
    "top_region_population_mmi_ge_6",
)

NARRATIVE_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "text": {"type": "string"},
        "metric_refs": {
            "type": "array",
            "items": {"type": "string", "enum": list(BRIEFING_METRICS)},
        },
        "region_refs": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": ["text", "metric_refs", "region_refs"],
    "additionalProperties": False,
}

BRIEFING_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "situation": {
            "type": "array",
            "items": NARRATIVE_ITEM_SCHEMA,
            "minItems": 2,
            "maxItems": 4,
        },
        "recommended_checks": {
            "type": "array",
            "items": NARRATIVE_ITEM_SCHEMA,
            "minItems": 1,
            "maxItems": 3,
        },
    },
    "required": ["situation", "recommended_checks"],
    "additionalProperties": False,
}
