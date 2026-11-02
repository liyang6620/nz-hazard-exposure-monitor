from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from hosts.azure_functions.function_app import _create_cloud_review_briefing


def _container():
    tables = Mock()
    tables.get_entity.return_value = None
    tables.list_entities.return_value = []
    draft_service = Mock()
    draft_service.draft.return_value = SimpleNamespace(
        fidelity_passed=True,
        payload={"headline": "Verified event briefing"},
        html="<main>Verified event briefing</main>",
        markdown="# Verified event briefing",
        map_image=None,
    )
    approval = Mock()
    container = SimpleNamespace(
        tables=tables,
        clock=SimpleNamespace(now=lambda: datetime(2026, 11, 2, tzinfo=UTC)),
        settings=SimpleNamespace(
            briefing_monthly_limit=10,
            notification_email="example@example.invalid",
            review_base_url="https://example.invalid/api/review-briefing",
        ),
        draft_briefing=lambda: draft_service,
        briefing_tools=SimpleNamespace(
            get_published_summary=lambda event_id: {"event_id": event_id, "magnitude": 7.8}
        ),
        approval=lambda: approval,
    )
    return container, draft_service, approval


def test_cloud_request_creates_one_fidelity_checked_pending_briefing():
    container, draft_service, approval = _container()
    _create_cloud_review_briefing(container, {"event_id": "2016p858000", "revision": 1})
    draft_service.draft.assert_called_once_with("2016p858000", briefing_id="2016p858000-r1")
    assert approval.create_pending.call_args.kwargs["title"] == "Verified event briefing"
    assert approval.create_pending.call_args.kwargs["source_magnitude"] == 7.8
    approval.supersede_older_revisions.assert_called_once()


def test_duplicate_request_does_not_call_the_model_or_send_mail():
    container, draft_service, approval = _container()
    container.tables.get_entity.return_value = {"status": "pending"}
    _create_cloud_review_briefing(container, {"event_id": "2016p858000"})
    draft_service.draft.assert_not_called()
    approval.create_pending.assert_not_called()


def test_monthly_limit_stops_before_model_call():
    container, draft_service, approval = _container()
    container.tables.list_entities.return_value = [
        {"created_at": "2026-11-01T00:00:00+00:00"} for _ in range(10)
    ]
    with pytest.raises(ValueError, match="Monthly briefing limit"):
        _create_cloud_review_briefing(container, {"event_id": "2016p858000"})
    draft_service.draft.assert_not_called()
    approval.create_pending.assert_not_called()


def test_failed_fidelity_never_sends_an_approval_link():
    container, draft_service, approval = _container()
    draft_service.draft.return_value.fidelity_passed = False
    with pytest.raises(ValueError, match="numeric fidelity"):
        _create_cloud_review_briefing(container, {"event_id": "2016p858000"})
    approval.create_pending.assert_not_called()


@pytest.mark.parametrize(
    "payload",
    [{"event_id": "../secret"}, {"event_id": "2016p858000", "revision": True}],
)
def test_invalid_request_is_rejected_before_model_call(payload):
    container, draft_service, _ = _container()
    with pytest.raises(ValueError):
        _create_cloud_review_briefing(container, payload)
    draft_service.draft.assert_not_called()
