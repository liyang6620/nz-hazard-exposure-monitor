resource "azurerm_consumption_budget_subscription" "spend_alert_1" {
  name            = "spend-alert-1"
  subscription_id = "/subscriptions/${var.subscription_id}"
  amount          = 2
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
    contact_emails = [var.contact_email]
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "azurerm_consumption_budget_subscription" "spend_alert_3" {
  name            = "spend-alert-3"
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
    contact_emails = [var.contact_email]
  }

  notification {
    enabled        = true
    threshold      = 100
    operator       = "GreaterThanOrEqualTo"
    threshold_type = "Forecasted"
    contact_emails = [var.contact_email]
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "azurerm_consumption_budget_subscription" "spend_alert_5" {
  name            = "spend-alert-5"
  subscription_id = "/subscriptions/${var.subscription_id}"
  amount          = 8
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
    contact_emails = [var.contact_email]
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "azurerm_consumption_budget_subscription" "action_group_drill" {
  name            = "nzhem-action-group-drill-2026-11"
  subscription_id = "/subscriptions/${var.subscription_id}"
  amount          = 1
  time_grain      = "Monthly"

  time_period {
    start_date = var.budget_start_date
    end_date   = "2026-12-01T00:00:00Z"
  }

  notification {
    enabled        = true
    threshold      = 100
    operator       = "GreaterThanOrEqualTo"
    threshold_type = "Actual"
    contact_groups = [var.budget_stop_action_group_id]
  }
}
