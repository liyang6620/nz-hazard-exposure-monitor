from datetime import UTC, datetime

import pytest

from nzhem.core.exposure import (
    building_valid_at,
    estimate_mmi,
    select_valid_buildings,
)

EVENT = datetime(2021, 3, 4, 19, 28, 32, tzinfo=UTC)


def test_lifecycle_uses_exact_half_open_event_time_interval() -> None:
    assert building_valid_at("2021-03-04T19:28:32Z", None, EVENT)
    assert not building_valid_at("2021-03-04T19:28:33Z", None, EVENT)
    assert not building_valid_at("2020-01-01T00:00:00Z", EVENT, EVENT)
    assert building_valid_at("2020-01-01T00:00:00Z", "2021-03-04T19:28:33Z", EVENT)
    assert not building_valid_at(None, None, EVENT)


def test_old_and_new_outline_for_one_building_never_count_twice() -> None:
    rows = [
        {
            "building_outline_id": 10,
            "building_id": 7,
            "begin_lifespan": "2019-01-01T00:00:00Z",
            "end_lifespan": "2021-01-01T00:00:00Z",
        },
        {
            "building_outline_id": 11,
            "building_id": 7,
            "begin_lifespan": "2021-01-01T00:00:00Z",
            "end_lifespan": None,
        },
    ]

    before = select_valid_buildings(rows, "2020-12-31T23:59:59Z")
    at_handover = select_valid_buildings(rows, "2021-01-01T00:00:00Z")

    assert [row["building_outline_id"] for row in before] == [10]
    assert [row["building_outline_id"] for row in at_handover] == [11]


def test_overlapping_source_versions_are_deduplicated_deterministically() -> None:
    rows = [
        {
            "building_outline_id": 20,
            "building_id": 8,
            "begin_lifespan": "2020-01-01",
            "end_lifespan": None,
        },
        {
            "building_outline_id": 21,
            "building_id": 8,
            "begin_lifespan": "2021-01-01",
            "end_lifespan": None,
        },
    ]

    selected = select_valid_buildings(rows, EVENT)

    assert [row["building_outline_id"] for row in selected] == [21]


@pytest.mark.parametrize(
    ("magnitude", "distance", "depth", "crustal", "expected_model", "expected"),
    [
        (4.9, 0.0, 0.0, True, "main_seismic_region_model_2", 7.0515718760),
        (5.5, 10.0, 5.0, True, "main_seismic_region_model_2", 7.6143071968),
        (6.0, 50.0, 10.0, True, "main_seismic_region_model_2", 6.2468772000),
        (6.5, 100.0, 15.0, True, "main_seismic_region_model_2", 5.8381322187),
        (7.8, 100.0, 15.0, True, "main_seismic_region_model_2", 7.4761322187),
        (8.2, 500.0, 50.0, True, "main_seismic_region_model_2", 5.8357731362),
        (5.0, 1.0, 70.0, True, "deep_region", 11.377),
        (5.5, 50.0, 100.0, True, "deep_region", 6.2636049848),
        (6.0, 100.0, 200.0, True, "deep_region", 6.2600000000),
        (7.0, 300.0, 300.0, True, "deep_region", 6.3800756085),
        (8.2, 1000.0, 350.0, True, "deep_region", 6.3260000000),
        (6.0, 100.0, 69.999, False, "main_seismic_region_model_2", 5.4591202187),
    ],
)
def test_locked_attenuation_vectors(
    magnitude: float,
    distance: float,
    depth: float,
    crustal: bool,
    expected_model: str,
    expected: float,
) -> None:
    result = estimate_mmi(
        magnitude=magnitude,
        distance_km=distance,
        depth_km=depth,
        crustal_event=crustal,
    )

    assert result.model == expected_model
    assert result.mmi == pytest.approx(expected, abs=1e-8)


def test_magnitude_outside_paper_dataset_is_not_extrapolated() -> None:
    below = estimate_mmi(magnitude=4.89, distance_km=20, depth_km=10)
    above = estimate_mmi(magnitude=8.21, distance_km=20, depth_km=10)

    assert below.mmi is None
    assert above.mmi is None
    assert below.exclusion_reason == "magnitude_outside_published_dataset"


@pytest.mark.parametrize("depth", [10.0, 100.0])
def test_attenuation_is_monotonic_in_distance_and_magnitude(depth: float) -> None:
    near = estimate_mmi(magnitude=6.0, distance_km=20, depth_km=depth)
    far = estimate_mmi(magnitude=6.0, distance_km=200, depth_km=depth)
    smaller = estimate_mmi(magnitude=5.5, distance_km=50, depth_km=depth)
    larger = estimate_mmi(magnitude=6.5, distance_km=50, depth_km=depth)

    assert near.mmi is not None and far.mmi is not None and near.mmi >= far.mmi
    assert smaller.mmi is not None and larger.mmi is not None and larger.mmi >= smaller.mmi
