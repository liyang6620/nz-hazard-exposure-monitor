locals {
  suffix = substr(sha256(var.subscription_id), 0, 8)

  names = {
    storage       = "stnzhem${local.suffix}"
    host_storage  = "stnzhemhost${local.suffix}"
    function_app  = "func-nzhem-${local.suffix}"
    service_plan  = "asp-nzhem-${local.suffix}"
    key_vault     = "kv-nzhem-${local.suffix}"
    log_analytics = "log-nzhem-${local.suffix}"
    app_insights  = "appi-nzhem-${local.suffix}"
    communication = "acs-nzhem-${local.suffix}"
    email         = "email-nzhem-${local.suffix}"
    openai        = "aoai-nzhem-${local.suffix}"
  }

  blob_container_names = toset([
    "raw",
    "curated",
    "gold",
    "briefings",
  ])
}
