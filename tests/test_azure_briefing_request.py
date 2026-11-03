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
            get_published_summary=lambda event_id: {
                "event_id": event_id,
                "magnitude": 7.8,
                "max_mmi": 8.4,
                "populated_max_mmi": 8.4,
                "as_if_today": True,
            }
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


def test_cloud_test_request_marks_draft_non_publishable():
    container, _, approval = _container()
    container.briefing_tools.get_published_summary = lambda event_id: {
        "event_id": event_id,
        "magnitude": 7.8,
        "max_mmi": 8.4,
        "as_if_today": True,
    }
    _create_cloud_review_briefing(
        container, {"event_id": "2016p858000", "revision": 9, "test_only": True}
    )
    assert approval.create_pending.call_args.kwargs["test_only"] is True


def test_test_request_cannot_bypass_trigger_for_live_event():
    container, draft_service, _ = _container()
    container.briefing_tools.get_published_summary = lambda event_id: {
        "event_id": event_id,
        "magnitude": 7.8,
        "max_mmi": 8.4,
        "as_if_today": False,
    }
    with pytest.raises(ValueError, match="historical replay"):
        _create_cloud_review_briefing(
            container, {"event_id": "2026p824047", "revision": 9, "test_only": True}
        )
    draft_service.draft.assert_not_called()


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


def test_remote_high_magnitude_without_populated_shaking_never_calls_llm():
    container, draft_service, approval = _container()
    container.briefing_tools.get_published_summary = lambda event_id: {
        "event_id": event_id,
        "magnitude": 5.0,
        "max_mmi": 7.0,
        "populated_max_mmi": 0.8,
        "has_populated_mmi_ge_5": False,
    }
    _create_cloud_review_briefing(container, {"event_id": "2026p824047"})
    draft_service.draft.assert_not_called()
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
