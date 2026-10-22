from azure.communication.email import EmailClient

from nzhem.config import Settings
from nzhem.identity import credential


def send_budget_stop_email(settings: Settings, run_id: str) -> None:
    client = EmailClient(settings.communication_endpoint, credential())
    message = {
        "senderAddress": settings.email_sender,
        "recipients": {"to": [{"address": settings.notification_email}]},
        "content": {
            "subject": "NZHEM budget stop activated",
            "plainText": (
                "The durable budget kill switch was enabled and the Function App stop "
                f"was requested. Run ID: {run_id}. Recovery is manual."
            ),
        },
    }
    client.begin_send(message).result()
