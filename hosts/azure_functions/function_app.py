from __future__ import annotations

import hashlib
import hmac
import json
import logging
import threading
import uuid
from collections import defaultdict
from datetime import UTC, datetime
from html import escape
from urllib.parse import urlsplit

import azure.functions as func

from nzhem.config import Settings
from nzhem.container import build_container
from nzhem.core.agent.approval import ApprovalRejected

app = func.FunctionApp()
_map_token_rate_lock = threading.Lock()
_map_token_rate_buckets: dict[tuple[str, str], int] = defaultdict(int)


def _no_store_headers() -> dict[str, str]:
    return {
        "Cache-Control": "no-store",
        "Content-Security-Policy": "default-src 'none'; form-action 'self'",
        "X-Content-Type-Options": "nosniff",
    }


def _invalid_review_response() -> func.HttpResponse:
    return func.HttpResponse(
        "<!doctype html><html lang='en'><meta charset='utf-8'>"
        "<main><h1>Review link unavailable</h1>"
        "<p>This link has expired, was already used, or is invalid.</p></main></html>",
        status_code=400,
        mimetype="text/html",
        headers=_no_store_headers(),
    )


def _client_ip(request: func.HttpRequest) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    return forwarded.split(",", 1)[0].strip() or "unknown"


def _map_request_origin_is_allowed(request: func.HttpRequest, allowed_origin: str) -> bool:
    origin = request.headers.get("origin", "").rstrip("/")
    if not origin or not hmac.compare_digest(origin, allowed_origin.rstrip("/")):
        return False
    referer = request.headers.get("referer", "")
    if not referer:
        return True
    parsed = urlsplit(referer)
    referer_origin = f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
    return hmac.compare_digest(referer_origin, allowed_origin.rstrip("/"))


def _map_rate_limit_allows(request: func.HttpRequest, limit: int) -> bool:
    minute = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M")
    client_hash = hashlib.sha256(_client_ip(request).encode("utf-8")).hexdigest()
    key = (minute, client_hash)
    with _map_token_rate_lock:
        stale = [bucket for bucket in _map_token_rate_buckets if bucket[0] != minute]
        for bucket in stale:
            del _map_token_rate_buckets[bucket]
        _map_token_rate_buckets[key] += 1
        return _map_token_rate_buckets[key] <= limit


@app.timer_trigger(
    schedule="%HOUSEKEEPING_SCHEDULE%",
    arg_name="timer",
    run_on_startup=True,
    use_monitor=True,
)
def housekeeping(timer: func.TimerRequest) -> None:
    del timer
    container = build_container()
    result = container.housekeeping().run()
    processor = container.event_processor()
    timed_out = processor.expire_stale_processing() if processor else 0
    publication = container.publish_site_data()
    logging.info(
        "housekeeping completed",
        extra={
            "run_id": result.run_id,
            "events_enqueued": result.events_enqueued,
            "timed_out": timed_out,
            "site_generation": publication["generation_id"] if publication else None,
        },
    )


@app.queue_trigger(arg_name="message", queue_name="events", connection="AzureWebJobsStorage")
def process_event(message: func.QueueMessage) -> None:
    container = build_container()
    processor = container.event_processor()
    if processor is None:
        raise RuntimeError("Azure event assessor is not configured")
    event = message.get_json()
    if not isinstance(event, dict):
        raise ValueError("Event queue payload must be a JSON object")
    status = processor.process_triggered(event, dequeue_count=message.dequeue_count)
    publication = container.publish_site_data()
    logging.info(
        "event processing completed",
        extra={"assessment_status": status, "site_generation": publication["generation_id"]},
    )


@app.route(
    route="budget-stop",
    trigger_arg_name="request",
    methods=["POST"],
    auth_level=func.AuthLevel.ANONYMOUS,
)
def budget_stop(request: func.HttpRequest) -> func.HttpResponse:
    settings = Settings.from_env()
    if settings.environment != "azure":
        return func.HttpResponse("budget-stop is Azure-only", status_code=501)
    supplied_token = request.params.get("token", "")
    if not supplied_token or not hmac.compare_digest(
        supplied_token,
        settings.budget_webhook_token,
    ):
        return func.HttpResponse("Forbidden", status_code=403)
    try:
        payload = request.get_json()
    except ValueError:
        return func.HttpResponse("Invalid JSON", status_code=400)
    if not isinstance(payload, dict) or payload.get("schemaId") != "azureMonitorCommonAlertSchema":
        return func.HttpResponse("Invalid alert payload", status_code=400)

    from nzhem.adapters.azure.budget import activate_budget_stop

    run_id = str(uuid.uuid4())
    activate_budget_stop(settings, run_id)
    return func.HttpResponse(
        json.dumps({"status": "stopping", "run_id": run_id}),
        status_code=202,
        mimetype="application/json",
    )


@app.route(
    route="review-briefing",
    trigger_arg_name="request",
    methods=["GET"],
    auth_level=func.AuthLevel.ANONYMOUS,
)
def review_briefing_get(request: func.HttpRequest) -> func.HttpResponse:
    token = request.params.get("token", "")
    try:
        preview = build_container().approval().preview(token, datetime.now(UTC))
    except (ApprovalRejected, KeyError, ValueError):
        return _invalid_review_response()
    html = (
        "<!doctype html><html lang='en'><meta charset='utf-8'><main>"
        f"<h1>{escape(preview.title)}</h1><p>Confirm {escape(preview.action)}.</p>"
        f"<form method='post' action='/api/review-briefing?token={escape(token)}'>"
        f"<button type='submit'>Confirm {escape(preview.action)}</button>"
        "</form></main></html>"
    )
    return func.HttpResponse(
        html,
        status_code=200,
        mimetype="text/html",
        headers=_no_store_headers(),
    )


@app.route(
    route="review-briefing",
    trigger_arg_name="request",
    methods=["POST"],
    auth_level=func.AuthLevel.ANONYMOUS,
)
def review_briefing_post(request: func.HttpRequest) -> func.HttpResponse:
    token = request.params.get("token", "")
    container = build_container()
    try:
        status = container.approval().decide(token, datetime.now(UTC), _client_ip(request))
    except (ApprovalRejected, KeyError, ValueError):
        return _invalid_review_response()
    if status == "approved":
        try:
            container.publish_site_data()
        except Exception:
            logging.exception(
                "approved briefing site publication failed; hourly retry remains active"
            )
            return func.HttpResponse(
                "<!doctype html><html lang='en'><main><h1>Briefing approved</h1>"
                "<p>The website update is pending. Please check again shortly.</p></main></html>",
                status_code=202,
                mimetype="text/html",
                headers=_no_store_headers(),
            )
    return func.HttpResponse(
        f"<!doctype html><html lang='en'><main><h1>Briefing {escape(status)}</h1></main></html>",
        status_code=200,
        mimetype="text/html",
        headers=_no_store_headers(),
    )


@app.route(
    route="map-token",
    trigger_arg_name="request",
    methods=["GET"],
    auth_level=func.AuthLevel.ANONYMOUS,
)
def map_token(request: func.HttpRequest) -> func.HttpResponse:
    settings = Settings.from_env()
    if not settings.map_token_enabled:
        return func.HttpResponse("Not found", status_code=404, headers=_no_store_headers())
    if not _map_request_origin_is_allowed(request, settings.map_token_allowed_origin):
        return func.HttpResponse("Forbidden", status_code=403, headers=_no_store_headers())
    if not _map_rate_limit_allows(request, settings.map_token_rate_limit_per_minute):
        return func.HttpResponse(
            "Too many requests",
            status_code=429,
            headers={**_no_store_headers(), "Retry-After": "60"},
        )

    # MG selected the token-free static GeoJSON map. Enabling a browser token
    # requires a separately approved, read-only OAuth broker implementation.
    return func.HttpResponse(
        "Token relay unavailable", status_code=503, headers=_no_store_headers()
    )
