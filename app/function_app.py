import json
import logging
import uuid

import azure.functions as func

from nzhem.arm import stop_function_app
from nzhem.config import Settings
from nzhem.killswitch import KillSwitch
from nzhem.notify import send_budget_stop_email
from nzhem.runlog import RunLog

app = func.FunctionApp()


@app.timer_trigger(
    schedule="%HOUSEKEEPING_SCHEDULE%",
    arg_name="timer",
    run_on_startup=True,
    use_monitor=True,
)
def housekeeping(timer: func.TimerRequest) -> None:
    settings = Settings.from_env()
    run_id = str(uuid.uuid4())
    switch = KillSwitch(settings)
    if switch.is_enabled():
        logging.warning("housekeeping skipped: kill switch enabled", extra={"run_id": run_id})
        return

    RunLog(settings).record_success(run_id=run_id, operation="housekeeping")
    logging.info("housekeeping completed", extra={"run_id": run_id})


@app.route(route="budget-stop", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
def budget_stop(request: func.HttpRequest) -> func.HttpResponse:
    settings = Settings.from_env()
    run_id = str(uuid.uuid4())

    try:
        payload = request.get_json()
    except ValueError:
        return func.HttpResponse("Invalid JSON", status_code=400)

    if not _is_action_group_request(payload):
        return func.HttpResponse("Invalid alert payload", status_code=400)

    switch = KillSwitch(settings)
    switch.enable(run_id=run_id, reason="budget_action_group")
    RunLog(settings).record_success(run_id=run_id, operation="budget_stop_switch")

    email_error = None
    try:
        send_budget_stop_email(settings, run_id)
    except Exception as exc:  # Email failure must not prevent the hard stop.
        email_error = type(exc).__name__
        logging.exception("budget stop email failed", extra={"run_id": run_id})

    stop_function_app(settings)
    body = {"status": "stopping", "run_id": run_id, "email_error": email_error}
    return func.HttpResponse(json.dumps(body), status_code=202, mimetype="application/json")


def _is_action_group_request(payload: object) -> bool:
    if not isinstance(payload, dict):
        return False
    schema_id = payload.get("schemaId")
    return schema_id == "azureMonitorCommonAlertSchema"
