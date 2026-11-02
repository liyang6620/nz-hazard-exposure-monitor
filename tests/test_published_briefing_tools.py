import json

import pytest

from nzhem.core.agent.published_briefing_tools import PublishedBriefingTools


class MemoryObjects:
    def __init__(self, blobs):
        self.blobs = blobs

    def get_bytes(self, container, path):
        return self.blobs[(container, path)]


def test_uses_the_manifest_selected_summary():
    generation = "20261101T230000282475Z"
    event_id = "2016p858000"
    objects = MemoryObjects(
        {
            ("web", "data/manifest.json"): json.dumps(
                {"generation_id": generation, "base_path": f"/data/generations/{generation}"}
            ).encode(),
            ("web", f"data/generations/{generation}/events/{event_id}/summary.json"): json.dumps(
                {"event_id": event_id, "buildings_mmi_ge_6": 78564}
            ).encode(),
        }
    )
    assert (
        PublishedBriefingTools(objects).get_published_summary(event_id)["buildings_mmi_ge_6"]
        == 78564
    )


@pytest.mark.parametrize("event_id", ["../secret", "2016p858000/other", "not-an-event"])
def test_rejects_untrusted_event_path(event_id):
    with pytest.raises(ValueError, match="Invalid GeoNet event ID"):
        PublishedBriefingTools(MemoryObjects({})).get_published_summary(event_id)


def test_rejects_mismatched_manifest_path():
    objects = MemoryObjects(
        {
            ("web", "data/manifest.json"): json.dumps(
                {"generation_id": "20261101T230000282475Z", "base_path": "/other"}
            ).encode()
        }
    )
    with pytest.raises(ValueError, match="base path"):
        PublishedBriefingTools(objects).get_published_summary("2016p858000")
