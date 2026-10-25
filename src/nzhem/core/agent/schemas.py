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

KEY_FIGURE_SCHEMA = {
    "type": "object",
    "properties": {
        "label": {"type": "string"},
        "value": {"type": "number"},
        "unit": {"type": "string"},
        "source_tool": {"type": "string", "enum": list(TOOL_SCHEMAS)},
        "source_field": {"type": "string"},
    },
    "required": ["label", "value", "unit", "source_tool", "source_field"],
    "additionalProperties": False,
}

BRIEFING_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "headline": {"type": "string"},
        "key_figures": {
            "type": "array",
            "items": KEY_FIGURE_SCHEMA,
            "minItems": 3,
            "maxItems": 5,
        },
        "regions_most_affected": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 3,
        },
        "then_vs_now": {"type": "string"},
        "limitations": {
            "type": "array",
            "items": {"type": "string", "enum": list(LIMITATIONS)},
            "minItems": 3,
            "maxItems": 3,
        },
        "recommended_checks": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 3,
        },
        "generated_at": {"type": "string", "format": "date-time"},
    },
    "required": [
        "headline",
        "key_figures",
        "regions_most_affected",
        "then_vs_now",
        "limitations",
        "recommended_checks",
        "generated_at",
    ],
    "additionalProperties": False,
}
