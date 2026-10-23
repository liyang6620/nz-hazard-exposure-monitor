from __future__ import annotations

from typing import Any

import requests

from nzhem.ports import SecretStore


class OpenAILlmClient:
    def __init__(self, secrets: SecretStore, *, api_key_name: str, model: str) -> None:
        self._secrets = secrets
        self._api_key_name = api_key_name
        self._model = model

    def generate(self, prompt: str, *, max_output_tokens: int) -> str:
        response = requests.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {self._secrets.get_secret(self._api_key_name)}",
                "Content-Type": "application/json",
            },
            json={
                "model": self._model,
                "input": prompt,
                "reasoning": {"effort": "minimal"},
                "max_output_tokens": max_output_tokens,
            },
            timeout=30,
        )
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
        return str(payload["output_text"])
