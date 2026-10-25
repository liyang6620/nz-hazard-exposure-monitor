from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests

from nzhem.ports import SecretStore


@dataclass(frozen=True)
class OpenAIUsage:
    input_tokens: int
    cached_input_tokens: int
    output_tokens: int
    total_tokens: int


class OpenAILlmClient:
    def __init__(self, secrets: SecretStore, *, api_key_name: str, model: str) -> None:
        self._secrets = secrets
        self._api_key_name = api_key_name
        self._model = model
        self._usage: list[OpenAIUsage] = []

    @property
    def usage(self) -> tuple[OpenAIUsage, ...]:
        return tuple(self._usage)

    def generate(
        self,
        prompt: str,
        *,
        max_output_tokens: int,
        response_schema: dict[str, Any] | None = None,
    ) -> str:
        request: dict[str, Any] = {
            "model": self._model,
            "input": prompt,
            "reasoning": {"effort": "minimal"},
            "max_output_tokens": max_output_tokens,
        }
        if response_schema is not None:
            request["text"] = {
                "format": {
                    "type": "json_schema",
                    "name": "nzhem_briefing",
                    "strict": True,
                    "schema": response_schema,
                }
            }
        response = requests.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {self._secrets.get_secret(self._api_key_name)}",
                "Content-Type": "application/json",
            },
            json=request,
            timeout=30,
        )
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
        usage = payload.get("usage") or {}
        if usage:
            input_details = usage.get("input_tokens_details") or {}
            input_tokens = int(usage.get("input_tokens", 0))
            output_tokens = int(usage.get("output_tokens", 0))
            self._usage.append(
                OpenAIUsage(
                    input_tokens=input_tokens,
                    cached_input_tokens=int(input_details.get("cached_tokens", 0)),
                    output_tokens=output_tokens,
                    total_tokens=int(usage.get("total_tokens", input_tokens + output_tokens)),
                )
            )
        output_text = str(payload.get("output_text", ""))
        if not output_text:
            output_text = "\n".join(
                str(content.get("text", ""))
                for item in payload.get("output", [])
                for content in item.get("content", [])
                if content.get("type") == "output_text" and content.get("text")
            )
        if not output_text:
            raise RuntimeError("OpenAI response did not contain output text")
        return output_text
