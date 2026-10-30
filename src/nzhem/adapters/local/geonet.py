from __future__ import annotations

import time
from collections.abc import Mapping, Sequence
from contextlib import suppress
from datetime import datetime
from io import StringIO
from typing import Any
from xml.etree import ElementTree

import requests

USER_AGENT = (
    "nz-hazard-exposure-monitor/0.1 (+https://github.com/liyang6620/nz-hazard-exposure-monitor)"
)
QUAKEML_BED_NAMESPACE = "http://quakeml.org/xmlns/bed/1.2"


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
            "minmagnitude": "4.0",
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
        enriched = []
        for event in events.values():
            latest = dict(event)
            with suppress(ElementTree.ParseError, KeyError, requests.RequestException, ValueError):
                latest.update(self._revision_metadata(str(event["event_id"])))
            enriched.append(latest)
        return enriched

    def _revision_metadata(self, event_id: str) -> dict[str, Any]:
        response = self._request({"eventid": event_id, "format": "xml"})
        return self._parse_revision_xml(response.text)

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
                    "magnitude_type": row.get("MagType") or None,
                    "magnitude_revision_time": None,
                    "depth_km": float(row.get("Depth/km") or row["Depth"]),
                    "latitude": float(row["Latitude"]),
                    "longitude": float(row["Longitude"]),
                    "event_name": row.get("EventLocationName", "New Zealand earthquake"),
                    "action": "upsert",
                }
            )
        return events

    @staticmethod
    def _parse_revision_xml(text: str) -> dict[str, Any]:
        namespace = f"{{{QUAKEML_BED_NAMESPACE}}}"
        root = ElementTree.fromstring(text)
        event = root.find(f".//{namespace}event")
        if event is None:
            raise ValueError("GeoNet QuakeML did not contain an event")
        magnitude_id = event.findtext(f"{namespace}preferredMagnitudeID")
        origin_id = event.findtext(f"{namespace}preferredOriginID")
        magnitude = next(
            (
                candidate
                for candidate in event.findall(f"{namespace}magnitude")
                if candidate.get("publicID") == magnitude_id
            ),
            None,
        )
        if magnitude is None:
            raise ValueError("GeoNet QuakeML did not contain the preferred magnitude")
        magnitude_value = magnitude.findtext(f"{namespace}mag/{namespace}value")
        magnitude_type = magnitude.findtext(f"{namespace}type")
        magnitude_revision_time = magnitude.findtext(
            f"{namespace}creationInfo/{namespace}creationTime"
        )
        if magnitude_value is None or magnitude_type is None or magnitude_revision_time is None:
            raise ValueError("GeoNet preferred magnitude metadata is incomplete")

        revision_times = [magnitude_revision_time]
        if origin_id:
            origin = next(
                (
                    candidate
                    for candidate in event.findall(f"{namespace}origin")
                    if candidate.get("publicID") == origin_id
                ),
                None,
            )
            if origin is not None:
                origin_revision_time = origin.findtext(
                    f"{namespace}creationInfo/{namespace}creationTime"
                )
                if origin_revision_time:
                    revision_times.append(origin_revision_time)

        return {
            "revision": max(revision_times),
            "magnitude": float(magnitude_value),
            "magnitude_type": magnitude_type,
            "magnitude_revision_time": magnitude_revision_time,
        }
