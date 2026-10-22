from dataclasses import dataclass


class BriefingLimitExceeded(RuntimeError):
    """Raised before an LLM call when a hard monthly or token cap is reached."""


@dataclass(frozen=True)
class BriefingUsage:
    briefings_this_month: int
    input_tokens: int
    output_tokens: int


def enforce_limits(
    usage: BriefingUsage,
    *,
    monthly_limit: int,
    total_token_limit: int,
    max_output_tokens: int,
) -> None:
    if usage.briefings_this_month >= monthly_limit:
        raise BriefingLimitExceeded("monthly briefing limit reached")
    if usage.input_tokens + max_output_tokens > total_token_limit:
        raise BriefingLimitExceeded("per-briefing token limit reached")
    if usage.output_tokens > max_output_tokens:
        raise BriefingLimitExceeded("output token limit reached")
