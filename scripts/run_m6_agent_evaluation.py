from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from nzhem.adapters.local.briefing_tools import DuckDbBriefingTools
from nzhem.adapters.local.openai import OpenAILlmClient, OpenAIUsage
from nzhem.core.agent.briefing import DraftBriefingService

ROOT = Path(__file__).resolve().parents[1]
MODEL = "gpt-5-mini"
INPUT_USD_PER_MILLION = 0.25
CACHED_INPUT_USD_PER_MILLION = 0.025
OUTPUT_USD_PER_MILLION = 2.0
HARD_BUDGET_USD = 1.0
PREVIOUS_M6_COST_USD = 0.0023465
UNRECORDED_CALL_RESERVE_USD = 0.0102
EVENT_IDS = (
    "3366146",
    "3468575",
    "3528839",
    "2013p543824",
    "2013p613797",
    "2014p051675",
    "2016p661332",
    "2016p858000",
    "2021p169764",
    "2026p776286",
)


@dataclass(frozen=True)
class ApiCallEvidence:
    estimated_input_tokens: int
    max_output_tokens: int
    estimated_cost_usd: float
    input_tokens: int
    cached_input_tokens: int
    output_tokens: int
    total_tokens: int
    actual_cost_usd: float


class MappingSecretStore:
    def __init__(self, values: dict[str, str]) -> None:
        self._values = values

    def get_secret(self, name: str) -> str:
        value = self._values.get(name, "")
        if not value:
            raise KeyError(name)
        return value


def load_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        values[name.strip()] = value.strip()
    return values


def estimate_tokens(text: str) -> int:
    return max(1, math.ceil(len(text) / 4))


def estimated_cost(input_tokens: int, max_output_tokens: int) -> float:
    return (
        input_tokens * INPUT_USD_PER_MILLION + max_output_tokens * OUTPUT_USD_PER_MILLION
    ) / 1_000_000


def actual_cost(usage: OpenAIUsage) -> float:
    uncached = max(0, usage.input_tokens - usage.cached_input_tokens)
    return (
        uncached * INPUT_USD_PER_MILLION
        + usage.cached_input_tokens * CACHED_INPUT_USD_PER_MILLION
        + usage.output_tokens * OUTPUT_USD_PER_MILLION
    ) / 1_000_000


class BudgetedLlmClient:
    def __init__(
        self,
        client: OpenAILlmClient,
        *,
        prior_cost_usd: float,
        hard_budget_usd: float,
    ) -> None:
        self._client = client
        self._hard_budget = hard_budget_usd
        self.cumulative_cost_usd = prior_cost_usd
        self.calls: list[ApiCallEvidence] = []

    def generate(
        self,
        prompt: str,
        *,
        max_output_tokens: int,
        response_schema: dict[str, Any] | None = None,
    ) -> str:
        input_estimate = estimate_tokens(prompt)
        cost_estimate = estimated_cost(input_estimate, max_output_tokens)
        if self.cumulative_cost_usd + cost_estimate > self._hard_budget:
            raise RuntimeError("M6 OpenAI hard budget would be exceeded")
        usage_before = len(self._client.usage)
        try:
            output = self._client.generate(
                prompt,
                max_output_tokens=max_output_tokens,
                response_schema=response_schema,
            )
        finally:
            usage_after = len(self._client.usage)
            if usage_after == usage_before + 1:
                usage = self._client.usage[-1]
                cost = actual_cost(usage)
                self.cumulative_cost_usd += cost
                self.calls.append(
                    ApiCallEvidence(
                        estimated_input_tokens=input_estimate,
                        max_output_tokens=max_output_tokens,
                        estimated_cost_usd=round(cost_estimate, 8),
                        input_tokens=usage.input_tokens,
                        cached_input_tokens=usage.cached_input_tokens,
                        output_tokens=usage.output_tokens,
                        total_tokens=usage.total_tokens,
                        actual_cost_usd=round(cost, 8),
                    )
                )
        if usage_after != usage_before + 1:
            raise RuntimeError("OpenAI response did not include token usage")
        if self.cumulative_cost_usd > self._hard_budget:
            raise RuntimeError("M6 OpenAI hard budget was exceeded")
        return output


def run_evaluation(
    *,
    api_key: str,
    event_root: Path,
    reference_root: Path,
    output_path: Path,
    max_output_tokens: int,
) -> dict[str, Any]:
    if len(EVENT_IDS) > 10:
        raise RuntimeError("M6 monthly briefing limit exceeded")
    tools = DuckDbBriefingTools(event_root, reference_root, memory_limit_mb=512)
    raw_client = OpenAILlmClient(
        MappingSecretStore({"OPENAI_API_KEY": api_key}),
        api_key_name="OPENAI_API_KEY",
        model=MODEL,
    )
    client = BudgetedLlmClient(
        raw_client,
        prior_cost_usd=PREVIOUS_M6_COST_USD + UNRECORDED_CALL_RESERVE_USD,
        hard_budget_usd=HARD_BUDGET_USD,
    )
    records: list[dict[str, Any]] = []
    try:
        service = DraftBriefingService(
            tools,
            client,
            max_output_tokens=max_output_tokens,
            total_token_limit=12000,
        )
        for event_id in EVENT_IDS:
            call_start = len(client.calls)
            cost_start = client.cumulative_cost_usd
            try:
                draft = service.draft(event_id)
            except Exception as exc:
                records.append(
                    {
                        "event_id": event_id,
                        "status": "failed",
                        "fidelity_passed": False,
                        "invalid_numbers_or_provenance": [],
                        "attempts": len(client.calls) - call_start,
                        "api_calls": len(client.calls) - call_start,
                        "actual_cost_usd": round(client.cumulative_cost_usd - cost_start, 8),
                        "error_type": type(exc).__name__,
                    }
                )
                break
            canonical = json.dumps(
                draft.payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")
            )
            records.append(
                {
                    "event_id": event_id,
                    "status": draft.status,
                    "fidelity_passed": draft.fidelity_passed,
                    "invalid_numbers_or_provenance": list(draft.invalid_numbers),
                    "attempts": draft.attempts,
                    "api_calls": len(client.calls) - call_start,
                    "actual_cost_usd": round(client.cumulative_cost_usd - cost_start, 8),
                    "payload_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
                }
            )
    finally:
        tools.close()
    passed = sum(record["fidelity_passed"] for record in records)
    result = {
        "model": MODEL,
        "reasoning_effort": "minimal",
        "max_output_tokens": max_output_tokens,
        "hard_budget_usd": HARD_BUDGET_USD,
        "previous_known_actual_cost_usd": PREVIOUS_M6_COST_USD,
        "unrecorded_call_budget_reserve_usd": UNRECORDED_CALL_RESERVE_USD,
        "this_run_cost_usd": round(
            client.cumulative_cost_usd - PREVIOUS_M6_COST_USD - UNRECORDED_CALL_RESERVE_USD,
            8,
        ),
        "known_cumulative_actual_cost_usd": round(
            client.cumulative_cost_usd - UNRECORDED_CALL_RESERVE_USD, 8
        ),
        "budget_accounted_cost_usd": round(client.cumulative_cost_usd, 8),
        "pricing_usd_per_million": {
            "input": INPUT_USD_PER_MILLION,
            "cached_input": CACHED_INPUT_USD_PER_MILLION,
            "output": OUTPUT_USD_PER_MILLION,
        },
        "pricing_source": "https://developers.openai.com/api/docs/models/gpt-5-mini",
        "events_evaluated": len(records),
        "fidelity_passed": passed,
        "numeric_fidelity_percent": round(100 * passed / len(records), 2),
        "records": records,
        "api_calls": [asdict(call) for call in client.calls],
        "api_key_logged": False,
        "azure_called": False,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the complete M6 ten-event evaluation")
    parser.add_argument("--event-root", type=Path, default=ROOT / ".local/data/curated/events/m3")
    parser.add_argument(
        "--reference-root",
        type=Path,
        default=ROOT / ".local/data/curated/reference-export/dee5b263952e",
    )
    parser.add_argument("--output", type=Path, default=ROOT / "evidence/m6/agent-evaluation.json")
    parser.add_argument("--max-output-tokens", type=int, default=1200)
    arguments = parser.parse_args()
    values = load_dotenv(ROOT / ".env")
    result = run_evaluation(
        api_key=values.get("OPENAI_API_KEY", ""),
        event_root=arguments.event_root,
        reference_root=arguments.reference_root,
        output_path=arguments.output,
        max_output_tokens=arguments.max_output_tokens,
    )
    print(
        json.dumps(
            {
                "events_evaluated": result["events_evaluated"],
                "numeric_fidelity_percent": result["numeric_fidelity_percent"],
                "known_cumulative_actual_cost_usd": result["known_cumulative_actual_cost_usd"],
                "budget_accounted_cost_usd": result["budget_accounted_cost_usd"],
            },
            sort_keys=True,
        )
    )
    if result["events_evaluated"] != len(EVENT_IDS) or result["numeric_fidelity_percent"] != 100:
        raise SystemExit("M6 ten-event evaluation did not meet its acceptance threshold")


if __name__ == "__main__":
    main()
