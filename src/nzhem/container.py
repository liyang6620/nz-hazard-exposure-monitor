from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

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
    ReferenceDataRefresher,
    ReferenceRefreshResult,
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
    reference_data: ReferenceDataRefresher | None = None

    def housekeeping(self) -> HousekeepingService:
        return HousekeepingService(
            clock=self.clock,
            tables=self.tables,
            queues=self.queues,
            event_source=self.event_source,
        )

    def refresh_reference(self) -> ReferenceRefreshResult:
        if self.reference_data is None:
            raise RuntimeError("Reference refresh is not configured for this deployment")
        from nzhem.core.reference import RefreshReferenceService

        return RefreshReferenceService(self.reference_data).run()


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
        LocalReferenceDataRefresher,
        LocalStaticSitePublisher,
        NullEventSource,
        OpenAILlmClient,
        SmtpMailer,
        SqliteQueueStore,
        SqliteTableStore,
    )

    objects = LocalObjectStore(settings.data_root)
    site_root = Path(__file__).resolve().parents[2] / "hosts" / "local" / "site"
    if site_root.is_dir():
        for source in sorted(path for path in site_root.rglob("*") if path.is_file()):
            relative = source.relative_to(site_root).as_posix()
            if relative == "index.html":
                try:
                    objects.get_bytes("web", relative)
                    continue
                except FileNotFoundError:
                    pass
            objects.put_bytes("web", relative, source.read_bytes())
    else:
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
        reference_data=LocalReferenceDataRefresher(settings, secrets),
    )


def _build_azure_container(settings: Settings) -> ServiceContainer:
    from nzhem.adapters.azure import build_azure_container

    return build_azure_container(settings)
