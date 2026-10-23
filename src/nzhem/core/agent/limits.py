from dataclasses import dataclass


class BriefingLimitExceeded(RuntimeError):
    pass


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
    if usage.input_tokens + usage.output_tokens > total_token_limit:
        raise BriefingLimitExceeded("per-briefing token limit exceeded")
    if usage.output_tokens > max_output_tokens:
        raise BriefingLimitExceeded("output token limit exceeded")
