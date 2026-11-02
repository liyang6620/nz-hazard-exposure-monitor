from __future__ import annotations

import json
import re
from typing import Any

from nzhem.ports import ObjectStore

_EVENT_ID = re.compile(r"[0-9]{4}p[0-9]+\Z")
_GENERATION_ID = re.compile(r"[0-9]{8}T[0-9]{6}[0-9]+Z\Z")


class PublishedBriefingTools:
    """Read the exact event summary currently selected by the site manifest."""

    def __init__(self, objects: ObjectStore) -> None:
        self._objects = objects

    def get_event(self, event_id: str) -> dict[str, Any]:
        return self.get_published_summary(event_id)

    def get_published_summary(self, event_id: str) -> dict[str, Any]:
        if not _EVENT_ID.fullmatch(event_id):
            raise ValueError("Invalid GeoNet event ID")
        manifest = json.loads(self._objects.get_bytes("web", "data/manifest.json"))
        generation = str(manifest["generation_id"])
        if not _GENERATION_ID.fullmatch(generation):
            raise ValueError("Invalid published generation ID")
        expected_base = f"/data/generations/{generation}"
        if manifest["base_path"] != expected_base:
            raise ValueError("Published manifest base path does not match its generation")
        path = f"data/generations/{generation}/events/{event_id}/summary.json"
        summary = json.loads(self._objects.get_bytes("web", path))
        if summary.get("event_id") != event_id:
            raise ValueError("Published event summary does not match the request")
        return summary
