from __future__ import annotations

from dataclasses import dataclass

from nzhem.config import Settings
from nzhem.core.clock import SystemClock
from nzhem.core.housekeeping import HousekeepingService
from nzhem.ports import (
    Clock,
    EventSource,
    LlmClient,
    Mailer,
    ObjectStore,
    QueueStore,
    SecretStore,
    StaticSitePublisher,
    TableStore,
)


@dataclass(frozen=True)
class ServiceContainer:
    settings: Settings
    clock: Clock
    objects: ObjectStore
    queues: QueueStore
    tables: TableStore
    secrets: SecretStore
    mailer: Mailer
    llm: LlmClient
    static_site: StaticSitePublisher
    event_source: EventSource

    def housekeeping(self) -> HousekeepingService:
        return HousekeepingService(
            clock=self.clock,
            tables=self.tables,
            queues=self.queues,
            event_source=self.event_source,
        )


def build_container(settings: Settings | None = None) -> ServiceContainer:
    active_settings = settings or Settings.from_env()
    if active_settings.environment == "local":
        return _build_local_container(active_settings)
    return _build_azure_container(active_settings)


def _build_local_container(settings: Settings) -> ServiceContainer:
    from nzhem.adapters.local import (
        EnvironmentSecretStore,
        GeoNetFdsnEventSource,
        LocalObjectStore,
        LocalStaticSitePublisher,
        NullEventSource,
        OpenAILlmClient,
        SmtpMailer,
        SqliteQueueStore,
        SqliteTableStore,
    )

    objects = LocalObjectStore(settings.data_root)
    try:
        objects.get_bytes("web", "index.html")
    except FileNotFoundError:
        objects.put_bytes(
            "web",
            "index.html",
            (
                b"<!doctype html><html lang='en'><meta charset='utf-8'>"
                b"<title>NZ Hazard Exposure Monitor</title>"
                b"<h1>NZ Hazard Exposure Monitor</h1>"
                b"<p>The local static site is running.</p>"
            ),
        )
    secrets = EnvironmentSecretStore()
    event_source: EventSource = (
        GeoNetFdsnEventSource(settings.geonet_fdsn_url)
        if settings.geonet_poll_enabled
        else NullEventSource()
    )
    return ServiceContainer(
        settings=settings,
        clock=SystemClock(),
        objects=objects,
        queues=SqliteQueueStore(
            settings.sqlite_path,
            visibility_timeout_seconds=settings.queue_visibility_timeout_seconds,
            max_dequeue_count=settings.queue_max_dequeue_count,
        ),
        tables=SqliteTableStore(settings.sqlite_path),
        secrets=secrets,
        mailer=SmtpMailer(settings.smtp_host, settings.smtp_port, settings.mail_from),
        llm=OpenAILlmClient(
            secrets,
            api_key_name=settings.openai_api_key_name,
            model=settings.openai_model,
        ),
        static_site=LocalStaticSitePublisher(objects),
        event_source=event_source,
    )


def _build_azure_container(settings: Settings) -> ServiceContainer:
    from nzhem.adapters.azure import build_azure_container

    return build_azure_container(settings)
