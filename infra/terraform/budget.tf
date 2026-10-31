resource "random_password" "budget_webhook_token" {
  length  = 32
  special = false
}

resource "random_password" "approval_token_key" {
  length  = 48
  special = false
}

resource "azurerm_monitor_action_group" "budget_stop" {
  name                = "ag-nzhem-budget-stop"
  resource_group_name = var.resource_group_name
  short_name          = "nzhemstop"
  tags                = var.tags

  email_receiver {
    name                    = "repository-owner"
    email_address           = var.notification_email
    use_common_alert_schema = true
  }

  webhook_receiver {
    name                    = "budget-stop-function"
    service_uri             = "https://${azurerm_function_app_flex_consumption.main.default_hostname}/api/budget-stop?token=${random_password.budget_webhook_token.result}"
    use_common_alert_schema = true
  }
}

resource "azurerm_consumption_budget_subscription" "killswitch" {
  name            = "budget-killswitch"
  subscription_id = "/subscriptions/${var.subscription_id}"
  amount          = 5
  time_grain      = "Monthly"

  time_period {
    start_date = var.budget_start_date
    end_date   = var.budget_end_date
  }

  notification {
    enabled        = true
    threshold      = 100
    operator       = "GreaterThanOrEqualTo"
    threshold_type = "Actual"
    contact_groups = [azurerm_monitor_action_group.budget_stop.id]
  }

  lifecycle {
    prevent_destroy = true
  }
}
