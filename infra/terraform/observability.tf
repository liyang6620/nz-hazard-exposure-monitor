resource "azurerm_log_analytics_workspace" "main" {
  name                = local.names.log_analytics
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = "PerGB2018"
  retention_in_days   = 30
  daily_quota_gb      = 0.1
  tags                = var.tags
}

resource "azurerm_application_insights" "main" {
  name                 = local.names.app_insights
  resource_group_name  = var.resource_group_name
  location             = var.location
  workspace_id         = azurerm_log_analytics_workspace.main.id
  application_type     = "web"
  sampling_percentage  = 20
  daily_data_cap_in_gb = 0.1
  retention_in_days    = 30
  tags                 = var.tags
}

resource "azurerm_monitor_action_group" "failure_email" {
  name                = "ag-nzhem-function-failure"
  resource_group_name = var.resource_group_name
  short_name          = "nzhemfail"
  tags                = var.tags

  email_receiver {
    name                    = "repository-owner"
    email_address           = var.notification_email
    use_common_alert_schema = true
  }
}

resource "azurerm_monitor_metric_alert" "function_failure" {
  name                = "nzhem-function-execution-failure"
  resource_group_name = var.resource_group_name
  scopes              = [azurerm_application_insights.main.id]
  description         = "At least one Function exception was reported in five minutes."
  severity            = 1
  frequency           = "PT5M"
  window_size         = "PT5M"
  auto_mitigate       = true
  tags                = var.tags

  criteria {
    metric_namespace = "Microsoft.Insights/components"
    metric_name      = "exceptions/count"
    aggregation      = "Count"
    operator         = "GreaterThan"
    threshold        = 0
  }

  action {
    action_group_id = azurerm_monitor_action_group.failure_email.id
  }
}

resource "azurerm_monitor_scheduled_query_rules_alert_v2" "housekeeping_missing" {
  name                    = "nzhem-housekeeping-missing"
  resource_group_name     = var.resource_group_name
  location                = var.location
  scopes                  = [azurerm_log_analytics_workspace.main.id]
  description             = "No successful housekeeping execution was logged in two hours."
  severity                = 1
  evaluation_frequency    = "PT30M"
  window_duration         = "PT2H"
  auto_mitigation_enabled = true
  tags                    = var.tags

  criteria {
    query                   = <<-KQL
      AppRequests
      | where Name == "housekeeping" and Success == true
      | summarize Executions = count()
    KQL
    metric_measure_column   = "Executions"
    time_aggregation_method = "Minimum"
    operator                = "LessThan"
    threshold               = 1

    failing_periods {
      minimum_failing_periods_to_trigger_alert = 1
      number_of_evaluation_periods             = 1
    }
  }

  action {
    action_groups = [azurerm_monitor_action_group.failure_email.id]
  }
}
