from __future__ import annotations

import re
from collections.abc import Iterable

FIXED_ROUTES = ("history", "method", "about")
_EVENT_ID = re.compile(r"[A-Za-z0-9_-]+\Z")


def static_route_blobs(event_ids: Iterable[str] = ()) -> list[str]:
    routes = list(FIXED_ROUTES)
    for event_id in event_ids:
        if not _EVENT_ID.fullmatch(event_id):
            raise ValueError("Invalid event ID for a static website route")
        routes.append(f"events/{event_id}")
    return [path for route in routes for path in (route, f"{route}/index.html")]
