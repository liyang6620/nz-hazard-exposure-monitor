from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from typing import Any

PAPER_MIN_MAGNITUDE = 4.9
PAPER_MAX_MAGNITUDE = 8.2
DEEP_SOURCE_BOUNDARY_KM = 70.0
MAX_MODEL_DEPTH_KM = 300.0
MIN_MODEL_DISTANCE_KM = 1.0


@dataclass(frozen=True)
class AttenuationResult:
    mmi: float | None
    model: str | None
    model_reference: str | None
    depth_km_used: float
    distance_km_used: float
    depth_clamped: bool
    distance_clamped: bool
    point_source_approx: bool
    exclusion_reason: str | None = None


def as_utc(value: datetime | date | str) -> datetime:
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if isinstance(value, date) and not isinstance(value, datetime):
        value = datetime.combine(value, time.min, tzinfo=UTC)
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def building_valid_at(
    begin_lifespan: datetime | date | str | None,
    end_lifespan: datetime | date | str | None,
    event_time: datetime | date | str,
) -> bool:
    """Return whether one LINZ outline is valid at the exact event timestamp."""
    if begin_lifespan is None:
        return False
    event = as_utc(event_time)
    begin = as_utc(begin_lifespan)
    end = as_utc(end_lifespan) if end_lifespan is not None else None
    return begin <= event and (end is None or end > event)


def select_valid_buildings(
    rows: Iterable[Mapping[str, Any]], event_time: datetime | date | str
) -> list[Mapping[str, Any]]:
    """Filter lifecycle rows and retain one deterministic outline per building."""
    selected: dict[Any, Mapping[str, Any]] = {}
    for row in rows:
        if not building_valid_at(row.get("begin_lifespan"), row.get("end_lifespan"), event_time):
            continue
        building_id = row["building_id"]
        previous = selected.get(building_id)
        if previous is None or _version_key(row) > _version_key(previous):
            selected[building_id] = row
    return list(selected.values())


def _version_key(row: Mapping[str, Any]) -> tuple[datetime, int]:
    begin = as_utc(row["begin_lifespan"])
    return begin, int(row.get("building_outline_id") or 0)


def haversine_km(
    latitude_a: float, longitude_a: float, latitude_b: float, longitude_b: float
) -> float:
    radius_km = 6371.0088
    phi_a = math.radians(latitude_a)
    phi_b = math.radians(latitude_b)
    delta_phi = math.radians(latitude_b - latitude_a)
    delta_lambda = math.radians(longitude_b - longitude_a)
    term = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi_a) * math.cos(phi_b) * math.sin(delta_lambda / 2) ** 2
    )
    return 2 * radius_km * math.asin(math.sqrt(term))


def estimate_mmi(
    *,
    magnitude: float,
    distance_km: float,
    depth_km: float,
    crustal_event: bool = True,
) -> AttenuationResult:
    """Apply the approved point-source approximation of the 2005 models.

    The main-seismic-region Model 2 and deep-region Model 3 are Table 6 and
    Table 7 respectively on page 198 of Dowrick and Rhoades (2005). The paper's
    dataset spans Mw 4.9-8.2; values outside that envelope are not extrapolated.
    """
    depth_used = min(max(depth_km, 0.0), MAX_MODEL_DEPTH_KM)
    distance_used = max(distance_km, MIN_MODEL_DISTANCE_KM)
    common = {
        "depth_km_used": depth_used,
        "distance_km_used": distance_used,
        "depth_clamped": depth_used != depth_km,
        "distance_clamped": distance_used != distance_km,
        "point_source_approx": magnitude >= 6.5,
    }
    if magnitude < PAPER_MIN_MAGNITUDE or magnitude > PAPER_MAX_MAGNITUDE:
        return AttenuationResult(
            mmi=None,
            model=None,
            model_reference=None,
            exclusion_reason="magnitude_outside_published_dataset",
            **common,
        )

    if depth_used >= DEEP_SOURCE_BOUNDARY_KM:
        mmi = 3.76 + 1.48 * magnitude - 3.50 * math.log10(distance_used) + 0.0031 * depth_used
        model = "deep_region"
        reference = "Dowrick and Rhoades (2005), Table 7, p. 198"
    else:
        effective_distance = (distance_used**3 + 11.78**3) ** (1 / 3)
        crustal_term = 0.409 if crustal_event else 0.0
        mmi = (
            4.40
            + 1.26 * magnitude
            - 3.67 * math.log10(effective_distance)
            + 0.012 * depth_used
            + crustal_term
        )
        model = "main_seismic_region_model_2"
        reference = "Dowrick and Rhoades (2005), Table 6, p. 198"
    return AttenuationResult(
        mmi=mmi,
        model=model,
        model_reference=reference,
        exclusion_reason=None,
        **common,
    )
