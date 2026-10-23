resource "azurerm_log_analytics_workspace" "main" {
  name                = local.names.log_analytics
  resource_group_name = azurerm_resource_group.production.name
  location            = azurerm_resource_group.production.location
  sku                 = "PerGB2018"
  retention_in_days   = 30
  daily_quota_gb      = 0.1
  tags                = var.tags
}

resource "azurerm_application_insights" "main" {
  name                 = local.names.app_insights
  resource_group_name  = azurerm_resource_group.production.name
  location             = azurerm_resource_group.production.location
  workspace_id         = azurerm_log_analytics_workspace.main.id
  application_type     = "web"
  sampling_percentage  = 20
  daily_data_cap_in_gb = 0.1
  retention_in_days    = 30
  tags                 = var.tags
}

resource "azurerm_monitor_action_group" "failure_email" {
  name                = "ag-nzhem-function-failure"
  resource_group_name = azurerm_resource_group.production.name
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
  resource_group_name = azurerm_resource_group.production.name
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
    aggregation      = "Total"
    operator         = "GreaterThan"
    threshold        = 0
  }

  action {
    action_group_id = azurerm_monitor_action_group.failure_email.id
  }
}
