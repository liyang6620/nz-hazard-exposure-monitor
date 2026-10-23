from __future__ import annotations

import json
import logging
import uuid

import azure.functions as func

from nzhem.config import Settings
from nzhem.container import build_container

app = func.FunctionApp()


@app.timer_trigger(
    schedule="%HOUSEKEEPING_SCHEDULE%",
    arg_name="timer",
    run_on_startup=False,
    use_monitor=True,
)
def housekeeping(timer: func.TimerRequest) -> None:
    del timer
    result = build_container().housekeeping().run()
    logging.info(
        "housekeeping completed",
        extra={"run_id": result.run_id, "events_enqueued": result.events_enqueued},
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
