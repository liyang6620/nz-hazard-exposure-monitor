from __future__ import annotations

import pytest

from nzhem.core.site_routes import static_route_blobs


def test_static_route_blobs_include_fixed_and_event_paths() -> None:
    assert static_route_blobs(["2016p858000"]) == [
        "history",
        "history/index.html",
        "method",
        "method/index.html",
        "about",
        "about/index.html",
        "events/2016p858000",
        "events/2016p858000/index.html",
    ]


@pytest.mark.parametrize("event_id", ["../secret", "bad/id", "bad?query"])
def test_static_route_blobs_reject_unsafe_event_ids(event_id: str) -> None:
    with pytest.raises(ValueError, match="Invalid event ID"):
        static_route_blobs([event_id])
