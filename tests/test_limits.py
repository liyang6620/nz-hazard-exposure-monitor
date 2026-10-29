import pytest

from nzhem.core.agent.limits import (
    BriefingLimitExceeded,
    BriefingUsage,
    enforce_limits,
    monthly_event_usage,
)


def test_usage_below_limits_is_allowed() -> None:
    enforce_limits(
        BriefingUsage(2, 800, 200),
        monthly_limit=10,
        total_token_limit=12000,
        max_output_tokens=1200,
    )


@pytest.mark.parametrize(
    ("usage", "message"),
    [
        (BriefingUsage(10, 0, 0), "monthly briefing"),
        (BriefingUsage(0, 11900, 101), "per-briefing token"),
        (BriefingUsage(0, 0, 1201), "output token"),
    ],
)
def test_hard_limits_reject_calls(usage: BriefingUsage, message: str) -> None:
    with pytest.raises(BriefingLimitExceeded, match=message):
        enforce_limits(
            usage,
            monthly_limit=10,
            total_token_limit=12000,
            max_output_tokens=1200,
        )


def test_revision_does_not_consume_another_monthly_event_slot() -> None:
    rows = [
        {"event_id": f"event-{index}", "created_at": "2026-10-28T00:00:00+00:00"}
        for index in range(10)
    ]

    assert monthly_event_usage(rows, "event-0", "2026-10") == 9
    assert monthly_event_usage(rows, "new-event", "2026-10") == 10
