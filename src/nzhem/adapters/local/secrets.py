from __future__ import annotations

import os


class EnvironmentSecretStore:
    def get_secret(self, name: str) -> str:
        value = os.getenv(name, "")
        if not value:
            raise KeyError(f"Required secret is not set: {name}")
        return value
