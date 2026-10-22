from functools import lru_cache

from azure.identity import DefaultAzureCredential


@lru_cache(maxsize=1)
def credential() -> DefaultAzureCredential:
    return DefaultAzureCredential(exclude_interactive_browser_credential=True)
