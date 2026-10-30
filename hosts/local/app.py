from __future__ import annotations

import json
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import UTC
from html import escape

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse

from nzhem.container import ServiceContainer, build_container
from nzhem.core.agent.approval import ApprovalRejected
from nzhem.core.agent.briefing import should_draft_briefing
from nzhem.core.agent.limits import BriefingUsage, enforce_limits, monthly_event_usage


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format='{"timestamp":"%(asctime)s","level":"%(levelname)s","message":%(message)s}',
    )


_configure_logging()
container: ServiceContainer = build_container()
scheduler = BackgroundScheduler(timezone="UTC")


def run_housekeeping() -> dict[str, object]:
    result = container.housekeeping().run()
    processing = container.process_events()
    site_publication = container.publish_site_data()
    payload = {
        "run_id": result.run_id,
        "catchup_from": result.catchup_from,
        "events_enqueued": result.events_enqueued,
        "briefings_expired": result.briefings_expired,
        "event_processing": processing.__dict__ if processing is not None else None,
        "site_generation": (
            site_publication.get("generation_id") if site_publication is not None else None
        ),
    }
    logging.info(json.dumps({"operation": "housekeeping", **payload}))
    return payload


@asynccontextmanager
async def lifespan(_: FastAPI):
    scheduler.add_job(
        run_housekeeping,
        "interval",
        minutes=container.settings.poll_interval_minutes,
        id="housekeeping",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
    scheduler.start()
    if container.settings.run_startup_housekeeping:
        try:
            run_housekeeping()
        except Exception:
            logging.exception("startup catch-up failed; the scheduled job will retry")
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)


app = FastAPI(title="NZ Hazard Exposure Monitor", version="0.1.0", lifespan=lifespan)

INVALID_REVIEW_HTML = (
    "<!doctype html><html lang='en'><meta charset='utf-8'>"
    "<meta name='viewport' content='width=device-width,initial-scale=1'>"
    "<title>Review link unavailable</title><main>"
    "<h1>Review link unavailable</h1>"
    "<p>This link has already been used, has expired, or has been replaced by a newer draft.</p>"
    "<p>Return to the latest review email to continue.</p></main></html>"
)


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "environment": container.settings.environment,
        "arcgis_publisher_enabled": container.settings.arcgis_publisher_enabled,
    }


@app.post("/housekeeping")
def housekeeping() -> dict[str, object]:
    try:
        return run_housekeeping()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=type(exc).__name__) from exc


@app.post("/refresh-reference")
def refresh_reference() -> dict[str, object]:
    try:
        result = container.refresh_reference()
        payload = {
            "source_buildings": result.source_buildings,
            "curated_buildings": result.curated_buildings,
            "source_population": result.source_population,
            "allocated_population": result.allocated_population,
            "rejected_buildings": result.rejected_buildings,
            "suppressed_sa1": result.suppressed_sa1,
            "elapsed_seconds": result.elapsed_seconds,
            "peak_rss_mb": result.peak_rss_mb,
            "minimum_free_disk_gb": result.minimum_free_disk_gb,
            "output_hashes": dict(result.output_hashes),
        }
        logging.info(json.dumps({"operation": "refresh_reference", **payload}))
        return payload
    except Exception as exc:
        logging.exception("reference refresh failed")
        raise HTTPException(status_code=503, detail=type(exc).__name__) from exc


@app.get("/runs")
def runs() -> list[dict[str, object]]:
    return list(container.tables.list_entities("runs"))


@app.post("/draft-briefing/{event_id}")
def draft_briefing(event_id: str, revision: bool = False) -> dict[str, object]:
    try:
        if container.briefing_tools is None:
            raise RuntimeError("M6 briefing data is not available")
        event = container.briefing_tools.get_event(event_id)
        event_briefings = [
            row
            for row in container.tables.list_entities("briefings", "briefing")
            if row.get("event_id") == event_id
        ]
        event_briefings.sort(key=lambda row: str(row["created_at"]), reverse=True)
        previous_magnitude = (
            float(event_briefings[0]["source_magnitude"])
            if event_briefings and event_briefings[0].get("source_magnitude") is not None
            else None
        )
        is_pending_revision = bool(
            revision and event_briefings and event_briefings[0].get("status") == "pending"
        )
        if not is_pending_revision and not should_draft_briefing(
            event, previous_magnitude=previous_magnitude
        ):
            raise ValueError("Event does not meet the briefing trigger")
        now = container.clock.now().astimezone(UTC)
        # A correction for an already-counted event does not consume another
        # event slot, while a new event still obeys the ten-event monthly cap.
        monthly = monthly_event_usage(
            list(container.tables.list_entities("briefings", "briefing")),
            event_id,
            now.strftime("%Y-%m"),
        )
        enforce_limits(
            BriefingUsage(monthly, 0, 0),
            monthly_limit=container.settings.briefing_monthly_limit,
            total_token_limit=container.settings.briefing_total_token_limit,
            max_output_tokens=container.settings.llm_max_output_tokens,
        )
        briefing_id = f"{event_id}-{uuid.uuid4().hex[:12]}"
        draft = container.draft_briefing().draft(event_id, briefing_id=briefing_id)
        pending = container.approval().create_pending(
            briefing_id=briefing_id,
            event_id=event_id,
            title=str(draft.payload["headline"]),
            html=draft.html,
            markdown=draft.markdown,
            map_image=draft.map_image,
            recipient=container.settings.notification_email,
            review_base_url=container.settings.review_base_url,
            now=now,
            needs_manual_review=not draft.fidelity_passed,
            revision=len(event_briefings) + 1,
            source_magnitude=float(event["magnitude"]),
        )
        return {
            "briefing_id": pending.briefing_id,
            "status": draft.status,
            "fidelity_passed": draft.fidelity_passed,
            "attempts": draft.attempts,
            "static_map": draft.map_status,
            "expires_at": pending.expires_at.isoformat(),
            "revision": len(event_briefings) + 1,
        }
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logging.exception("briefing draft failed")
        raise HTTPException(status_code=503, detail=type(exc).__name__) from exc


@app.get("/review-briefing", response_class=HTMLResponse)
def review_briefing_get(token: str) -> HTMLResponse:
    try:
        preview = container.approval().preview(token, container.clock.now())
    except (ApprovalRejected, KeyError, ValueError):
        return HTMLResponse(INVALID_REVIEW_HTML, status_code=400)
    return HTMLResponse(
        "<!doctype html><html lang='en'><meta charset='utf-8'><main>"
        f"<h1>{escape(preview.title)}</h1><p>Confirm {escape(preview.action)}.</p>"
        f"<form method='post' action='/review-briefing?token={escape(token)}'>"
        f"<button type='submit'>Confirm {escape(preview.action)}</button></form></main></html>"
    )


@app.post("/review-briefing", response_class=HTMLResponse)
def review_briefing_post(token: str, request: Request) -> HTMLResponse:
    try:
        status = container.approval().decide(
            token,
            container.clock.now(),
            request.client.host if request.client else "unknown",
        )
    except (ApprovalRejected, KeyError, ValueError):
        return HTMLResponse(INVALID_REVIEW_HTML, status_code=400)
    return HTMLResponse(
        f"<!doctype html><html lang='en'><main><h1>Briefing {escape(status)}</h1></main></html>"
    )


@app.get("/briefings")
def briefings() -> list[dict[str, object]]:
    return list(container.tables.list_entities("briefings", "briefing"))
