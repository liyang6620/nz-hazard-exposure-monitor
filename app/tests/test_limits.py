import pytest

from nzhem.agent.limits import BriefingLimitExceeded, BriefingUsage, enforce_limits


def test_usage_below_all_limits_is_allowed() -> None:
    enforce_limits(
        BriefingUsage(briefings_this_month=2, input_tokens=800, output_tokens=200),
        monthly_limit=10,
        total_token_limit=12000,
        max_output_tokens=1200,
    )


@pytest.mark.parametrize(
    ("usage", "message"),
    [
        (BriefingUsage(10, 0, 0), "monthly briefing"),
        (BriefingUsage(0, 11900, 0), "per-briefing token"),
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
