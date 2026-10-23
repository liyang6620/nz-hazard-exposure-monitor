from __future__ import annotations

from functools import lru_cache

import requests
from azure.communication.email import EmailClient
from azure.data.tables import TableServiceClient
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.storage.blob import BlobServiceClient
from azure.storage.queue import QueueServiceClient

from nzhem.adapters.local.geonet import GeoNetFdsnEventSource, NullEventSource
from nzhem.config import Settings
from nzhem.container import ServiceContainer
from nzhem.core.clock import SystemClock
from nzhem.ports import QueueMessage


@lru_cache(maxsize=1)
def credential() -> DefaultAzureCredential:
    return DefaultAzureCredential(exclude_interactive_browser_credential=True)


class AzureObjectStore:
    def __init__(self, account_name: str) -> None:
        endpoint = f"https://{account_name}.blob.core.windows.net"
        self._service = BlobServiceClient(endpoint, credential=credential())

    def put_bytes(self, container: str, path: str, data: bytes) -> None:
        actual_container = "$web" if container == "web" else container
        self._service.get_blob_client(actual_container, path).upload_blob(data, overwrite=True)

    def get_bytes(self, container: str, path: str) -> bytes:
        actual_container = "$web" if container == "web" else container
        return self._service.get_blob_client(actual_container, path).download_blob().readall()


class AzureStaticSitePublisher:
    def __init__(self, objects: AzureObjectStore) -> None:
        self._objects = objects

    def publish(self, path: str, content: bytes) -> None:
        self._objects.put_bytes("web", path, content)


class AzureTableStore:
    def __init__(self, account_name: str) -> None:
        endpoint = f"https://{account_name}.table.core.windows.net"
        self._service = TableServiceClient(endpoint, credential=credential())

    def upsert_entity(self, table_name: str, entity: dict) -> None:
        self._service.get_table_client(table_name).upsert_entity(entity, mode="replace")

    def get_entity(self, table_name: str, partition_key: str, row_key: str) -> dict | None:
        from azure.core.exceptions import ResourceNotFoundError

        try:
            entity = self._service.get_table_client(table_name).get_entity(partition_key, row_key)
        except ResourceNotFoundError:
            return None
        return dict(entity)

    def list_entities(self, table_name: str, partition_key: str | None = None) -> list[dict]:
        parameters = None
        query_filter = None
        if partition_key is not None:
            query_filter = "PartitionKey eq @partition"
            parameters = {"partition": partition_key}
        entities = self._service.get_table_client(table_name).query_entities(
            query_filter=query_filter,
            parameters=parameters,
        )
        return [dict(entity) for entity in entities]


class AzureQueueStore:
    def __init__(self, account_name: str, *, visibility_timeout: int, max_dequeues: int) -> None:
        endpoint = f"https://{account_name}.queue.core.windows.net"
        self._service = QueueServiceClient(endpoint, credential=credential())
        self._visibility_timeout = visibility_timeout
        self._max_dequeues = max_dequeues

    def send(self, queue_name: str, payload: dict) -> str:
        import json

        result = self._service.get_queue_client(queue_name).send_message(json.dumps(payload))
        return str(result.id)

    def receive(self, queue_name: str) -> QueueMessage | None:
        import json

        client = self._service.get_queue_client(queue_name)
        messages = client.receive_messages(
            messages_per_page=1,
            visibility_timeout=self._visibility_timeout,
        )
        message = next(iter(messages), None)
        if message is None:
            return None
        if message.dequeue_count > self._max_dequeues:
            self.send(f"{queue_name}-poison", json.loads(message.content))
            client.delete_message(message.id, message.pop_receipt)
            return self.receive(queue_name)
        return QueueMessage(
            message_id=message.id,
            payload=json.loads(message.content),
            dequeue_count=message.dequeue_count,
            receipt=message.pop_receipt,
        )

    def complete(self, queue_name: str, message_id: int | str, receipt: str) -> None:
        self._service.get_queue_client(queue_name).delete_message(str(message_id), receipt)

    def abandon(self, queue_name: str, message_id: int | str, receipt: str) -> None:
        self._service.get_queue_client(queue_name).update_message(
            str(message_id), receipt, visibility_timeout=0
        )


class AzureSecretStore:
    def __init__(self, vault_url: str) -> None:
        self._client = SecretClient(vault_url, credential=credential())

    def get_secret(self, name: str) -> str:
        return self._client.get_secret(name).value


class AzureMailer:
    def __init__(self, endpoint: str, sender: str) -> None:
        self._client = EmailClient(endpoint, credential())
        self._sender = sender

    def send(self, recipient: str, subject: str, text: str) -> None:
        self._client.begin_send(
            {
                "senderAddress": self._sender,
                "recipients": {"to": [{"address": recipient}]},
                "content": {"subject": subject, "plainText": text},
            }
        ).result()


class AzureOpenAILlmClient:
    _SCOPE = "https://cognitiveservices.azure.com/.default"

    def __init__(self, endpoint: str, deployment: str) -> None:
        self._endpoint = endpoint.rstrip("/")
        self._deployment = deployment

    def generate(self, prompt: str, *, max_output_tokens: int) -> str:
        token = credential().get_token(self._SCOPE).token
        response = requests.post(
            f"{self._endpoint}/openai/responses?api-version=2025-04-01-preview",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "model": self._deployment,
                "input": prompt,
                "reasoning": {"effort": "minimal"},
                "max_output_tokens": max_output_tokens,
            },
            timeout=30,
        )
        response.raise_for_status()
        return str(response.json()["output_text"])


def build_azure_container(settings: Settings) -> ServiceContainer:
    objects = AzureObjectStore(settings.storage_account_name)
    event_source = (
        GeoNetFdsnEventSource(settings.geonet_fdsn_url)
        if settings.geonet_poll_enabled
        else NullEventSource()
    )
    return ServiceContainer(
        settings=settings,
        clock=SystemClock(),
        objects=objects,
        queues=AzureQueueStore(
            settings.storage_account_name,
            visibility_timeout=settings.queue_visibility_timeout_seconds,
            max_dequeues=settings.queue_max_dequeue_count,
        ),
        tables=AzureTableStore(settings.storage_account_name),
        secrets=AzureSecretStore(settings.key_vault_url),
        mailer=AzureMailer(settings.communication_endpoint, settings.email_sender),
        llm=AzureOpenAILlmClient(
            settings.azure_openai_endpoint,
            settings.azure_openai_deployment,
        ),
        static_site=AzureStaticSitePublisher(objects),
        event_source=event_source,
    )
