import pytest
from scripts.run_m6_agent_evaluation import (
    BudgetedLlmClient,
    actual_cost,
    estimated_cost,
)

from nzhem.adapters.local.openai import OpenAIUsage


def test_costs_use_published_gpt5_mini_rates() -> None:
    usage = OpenAIUsage(1000, 400, 500, 1500)

    assert estimated_cost(1000, 500) == pytest.approx(0.00125)
    assert actual_cost(usage) == pytest.approx(0.00116)


def test_budget_guard_checks_before_call_and_records_actual_usage() -> None:
    class RecordingClient:
        def __init__(self) -> None:
            self.usage: tuple[OpenAIUsage, ...] = ()
            self.called = False

        def generate(self, *args, **kwargs) -> str:
            self.called = True
            self.usage = (*self.usage, OpenAIUsage(100, 0, 10, 110))
            return "{}"

    raw = RecordingClient()
    guarded = BudgetedLlmClient(raw, prior_cost_usd=0.999, hard_budget_usd=1.0)

    with pytest.raises(RuntimeError, match="would be exceeded"):
        guarded.generate("x" * 4000, max_output_tokens=500)
    assert raw.called is False

    guarded = BudgetedLlmClient(raw, prior_cost_usd=0.0, hard_budget_usd=1.0)
    assert guarded.generate("brief", max_output_tokens=100) == "{}"
    assert guarded.calls[0].total_tokens == 110
