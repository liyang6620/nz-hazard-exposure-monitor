from __future__ import annotations

import time
from collections.abc import Mapping, Sequence
from datetime import datetime
from io import StringIO
from typing import Any

import requests

USER_AGENT = (
    "nz-hazard-exposure-monitor/0.1 (+https://github.com/liyang6620/nz-hazard-exposure-monitor)"
)


class NullEventSource:
    def fetch_updated_after(self, updated_after: datetime) -> Sequence[Mapping[str, Any]]:
        return []


class GeoNetFdsnEventSource:
    def __init__(self, url: str, *, timeout_seconds: int = 30) -> None:
        self._url = url
        self._timeout_seconds = timeout_seconds

    def fetch_updated_after(self, updated_after: datetime) -> Sequence[Mapping[str, Any]]:
        common_parameters = {
            "format": "text",
            "updatedafter": updated_after.isoformat().replace("+00:00", "Z"),
            "minmagnitude": "3.5",
            "minlatitude": "-50",
            "maxlatitude": "-25",
        }
        events: dict[str, Mapping[str, Any]] = {}
        for minimum_longitude, maximum_longitude in (("160", "180"), ("-180", "-170")):
            parameters = {
                **common_parameters,
                "minlongitude": minimum_longitude,
                "maxlongitude": maximum_longitude,
            }
            response = self._request(parameters)
            for event in self._parse_text(response.text, updated_after):
                events[str(event["event_id"])] = event
        return list(events.values())

    def _request(self, parameters: Mapping[str, str]) -> requests.Response:
        last_error: requests.RequestException | None = None
        for attempt in range(3):
            try:
                response = requests.get(
                    self._url,
                    params=parameters,
                    headers={"User-Agent": USER_AGENT},
                    timeout=self._timeout_seconds,
                )
                response.raise_for_status()
                return response
            except requests.RequestException as exc:
                last_error = exc
                if attempt < 2:
                    time.sleep(2**attempt)
        assert last_error is not None
        raise last_error

    @staticmethod
    def _parse_text(text: str, updated_after: datetime) -> list[dict[str, Any]]:
        lines = [line for line in StringIO(text) if line.strip()]
        if not lines:
            return []
        headers = [header.strip().lstrip("#") for header in lines[0].split("|")]
        events = []
        for line in lines[1:]:
            values = [value.strip() for value in line.split("|")]
            row = dict(zip(headers, values, strict=True))
            events.append(
                {
                    "event_id": row["EventID"],
                    "revision": updated_after.isoformat(),
                    "event_time": row["Time"],
                    "magnitude": float(row["Magnitude"]),
                    "action": "upsert",
                }
            )
        return events
