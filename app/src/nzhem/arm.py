import requests

from nzhem.config import Settings
from nzhem.identity import credential

ARM_SCOPE = "https://management.azure.com/.default"
API_VERSION = "2024-11-01"


def stop_function_app(settings: Settings) -> None:
    token = credential().get_token(ARM_SCOPE).token
    url = (
        "https://management.azure.com/subscriptions/"
        f"{settings.subscription_id}/resourceGroups/{settings.resource_group_name}"
        f"/providers/Microsoft.Web/sites/{settings.function_app_name}/stop"
        f"?api-version={API_VERSION}"
    )
    response = requests.post(
        url,
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    response.raise_for_status()
