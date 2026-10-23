from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, HTTPException

from nzhem.container import ServiceContainer, build_container


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
    payload = {
        "run_id": result.run_id,
        "catchup_from": result.catchup_from,
        "events_enqueued": result.events_enqueued,
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


@app.get("/runs")
def runs() -> list[dict[str, object]]:
    return list(container.tables.list_entities("runs"))
