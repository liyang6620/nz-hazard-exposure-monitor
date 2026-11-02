from __future__ import annotations

import pytest

from nzhem.core.site_routes import static_route_blobs


def test_static_route_blobs_include_fixed_and_event_paths() -> None:
    assert static_route_blobs(["2016p858000"]) == [
        "history",
        "method",
        "about",
        "review",
        "events/2016p858000",
    ]


@pytest.mark.parametrize("event_id", ["../secret", "bad/id", "bad?query"])
def test_static_route_blobs_reject_unsafe_event_ids(event_id: str) -> None:
    with pytest.raises(ValueError, match="Invalid event ID"):
        static_route_blobs([event_id])
