from __future__ import annotations

import argparse
import json
import math
import os
import smtplib
from dataclasses import asdict, dataclass
from email.message import EmailMessage
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]
MODEL = "gpt-5-mini"
INPUT_USD_PER_MILLION = 0.25
OUTPUT_USD_PER_MILLION = 2.0
HARD_BUDGET_USD = 1.0


@dataclass(frozen=True)
class CallRecord:
    name: str
    estimated_input_tokens: int
    estimated_output_tokens: int
    estimated_cost_usd: float
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    actual_cost_usd: float | None
    status: str
    response_text: str | None = None
    error: str | None = None


def load_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        values[name.strip()] = value.strip()
    return values


def estimate_tokens(text: str) -> int:
    # Four characters per token is deliberately conservative for English and data labels.
    return max(1, math.ceil(len(text) / 4))


def estimate_cost(input_tokens: int, output_tokens: int) -> float:
    return (
        input_tokens * INPUT_USD_PER_MILLION + output_tokens * OUTPUT_USD_PER_MILLION
    ) / 1_000_000


def actual_cost(input_tokens: int, output_tokens: int) -> float:
    return estimate_cost(input_tokens, output_tokens)


def call_model(api_key: str, prompt: str, max_output_tokens: int) -> tuple[str, int, int, int]:
    response = requests.post(
        "https://api.openai.com/v1/responses",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": MODEL,
            "input": prompt,
            "reasoning": {"effort": "minimal"},
            "max_output_tokens": max_output_tokens,
        },
        timeout=60,
    )
    response.raise_for_status()
    payload: dict[str, Any] = response.json()
    usage = payload.get("usage") or {}
    input_tokens = int(usage["input_tokens"])
    output_tokens = int(usage["output_tokens"])
    total_tokens = int(usage.get("total_tokens", input_tokens + output_tokens))
    output_text = str(payload.get("output_text", ""))
    if not output_text:
        chunks = [
            str(content.get("text", ""))
            for item in payload.get("output", [])
            for content in item.get("content", [])
            if content.get("type") == "output_text"
        ]
        output_text = "\n".join(chunk for chunk in chunks if chunk)
    return output_text, input_tokens, output_tokens, total_tokens


def send_mailpit(
    host: str, port: int, sender: str, recipient: str, subject: str, body: str
) -> None:
    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)
    with smtplib.SMTP(host, port, timeout=10) as client:
        client.send_message(message)


def run_evaluation(
    *,
    api_key: str,
    output_path: Path,
    mailpit_host: str,
    mailpit_port: int,
    mail_from: str,
    mail_to: str,
    max_output_tokens: int,
) -> dict[str, Any]:
    prompts = [
        (
            "executive_summary",
            """You are reviewing NZHEM's local M3 evidence. In at most six bullet points,
summarise the as-if-today exposure result for a project manager. Use only these facts:
3,219,311 current deduplicated buildings, 4,994,034 fixed 2023 SA1 population,
ten official GeoNet shaking surfaces, eight pre-2018 event-time counts unsupported,
and point-source MAE 1.049 MMI. State that MAE is a known limitation.""",
        ),
        (
            "quality_review",
            """Review these NZHEM quality controls in at most 120 words: event-time lifecycle
is half-open and deduplicated by building_id; unsupported pre-2018 event-time values are
NULL/not_supported; DuckDB is capped at 512 MB and process RSS at 768 MB; the local map
uses official surfaces. Identify one residual risk without inventing measurements.""",
        ),
        (
            "owner_actions",
            """Draft a concise owner action list for NZHEM after local M3/MG/M5 work.
Mention that ArcGIS hosted publishing permissions are not proven by read-only checks,
Power BI screenshots/PDF are still owner actions, Azure/Terraform remain deferred, and
the D23 MAE 1.049 review is open. Do not suggest enabling billing.""",
        ),
    ]
    previous: dict[str, Any] = {}
    if output_path.exists():
        try:
            previous = json.loads(output_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            previous = {}
    records: list[CallRecord] = []
    cumulative_estimate = float(previous.get("estimated_cost_usd_before_calls", 0.0))
    cumulative_actual = float(previous.get("actual_cost_usd", 0.0))
    for name, prompt in prompts:
        estimated_input = estimate_tokens(prompt)
        estimated = estimate_cost(estimated_input, max_output_tokens)
        if cumulative_actual + estimated > HARD_BUDGET_USD:
            records.append(
                CallRecord(
                    name=name,
                    estimated_input_tokens=estimated_input,
                    estimated_output_tokens=max_output_tokens,
                    estimated_cost_usd=estimated,
                    input_tokens=None,
                    output_tokens=None,
                    total_tokens=None,
                    actual_cost_usd=None,
                    status="skipped_budget",
                )
            )
            continue
        cumulative_estimate += estimated
        try:
            output, input_tokens, output_tokens, total_tokens = call_model(
                api_key, prompt, max_output_tokens
            )
            cost = actual_cost(input_tokens, output_tokens)
            if cumulative_actual + cost > HARD_BUDGET_USD:
                raise RuntimeError("actual usage would exceed the US$1 hard cap")
            cumulative_actual += cost
            records.append(
                CallRecord(
                    name=name,
                    estimated_input_tokens=estimated_input,
                    estimated_output_tokens=max_output_tokens,
                    estimated_cost_usd=estimated,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                    actual_cost_usd=cost,
                    status="success",
                    response_text=output,
                )
            )
        except Exception as exc:  # pragma: no cover - network failure is recorded for operations
            records.append(
                CallRecord(
                    name=name,
                    estimated_input_tokens=estimated_input,
                    estimated_output_tokens=max_output_tokens,
                    estimated_cost_usd=estimated,
                    input_tokens=None,
                    output_tokens=None,
                    total_tokens=None,
                    actual_cost_usd=None,
                    status="failed",
                    error=type(exc).__name__,
                )
            )
            break

    successful = [record for record in records if record.status == "success"]
    mail_status = "not_sent"
    if successful:
        body = "\n\n".join(
            f"## {record.name}\n{record.response_text or ''}" for record in successful
        )
        try:
            send_mailpit(
                mailpit_host,
                mailpit_port,
                mail_from,
                mail_to,
                "NZHEM M6 local approval draft",
                body,
            )
            mail_status = "sent_to_local_mailpit"
        except Exception as exc:  # pragma: no cover - local service availability varies
            mail_status = f"failed:{type(exc).__name__}"
    result = {
        "model": MODEL,
        "pricing_usd_per_million": {
            "input": INPUT_USD_PER_MILLION,
            "cached_input": 0.025,
            "output": OUTPUT_USD_PER_MILLION,
        },
        "hard_budget_usd": HARD_BUDGET_USD,
        "estimated_cost_usd_before_calls": round(cumulative_estimate, 8),
        "actual_cost_usd": round(cumulative_actual, 8),
        "mailpit_status": mail_status,
        "mailpit_host": mailpit_host,
        "records": [*previous.get("records", []), *(asdict(record) for record in records)],
        "api_key_logged": False,
        "azure_called": False,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the budgeted local M6 OpenAI evaluation")
    parser.add_argument("--output", type=Path, default=ROOT / "evidence/m6/openai-evaluation.json")
    parser.add_argument("--max-output-tokens", type=int, default=450)
    parser.add_argument("--mailpit-host", default=os.getenv("SMTP_HOST", "127.0.0.1"))
    parser.add_argument("--mailpit-port", type=int, default=int(os.getenv("SMTP_PORT", "1025")))
    arguments = parser.parse_args()
    values = load_dotenv(ROOT / ".env")
    api_key = values.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is required in ignored .env or the environment")
    result = run_evaluation(
        api_key=api_key,
        output_path=arguments.output.resolve(),
        mailpit_host=arguments.mailpit_host,
        mailpit_port=arguments.mailpit_port,
        mail_from=values.get("MAIL_FROM", "nzhem@example.invalid"),
        mail_to=values.get("NOTIFICATION_EMAIL", "owner@example.invalid"),
        max_output_tokens=arguments.max_output_tokens,
    )
    print(
        json.dumps(
            {
                "model": result["model"],
                "actual_cost_usd": result["actual_cost_usd"],
                "mailpit_status": result["mailpit_status"],
                "record_statuses": [record["status"] for record in result["records"]],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
