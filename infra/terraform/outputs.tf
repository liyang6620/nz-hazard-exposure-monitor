output "resource_group_name" {
  value = var.resource_group_name
}

output "storage_account_name" {
  value     = azurerm_storage_account.data.name
  sensitive = true
}

output "function_app_name" {
  value     = azurerm_function_app_flex_consumption.main.name
  sensitive = true
}

output "function_app_default_hostname" {
  value     = azurerm_function_app_flex_consumption.main.default_hostname
  sensitive = true
}

output "key_vault_name" {
  value     = azurerm_key_vault.main.name
  sensitive = true
}

output "azure_openai_account_name" {
  value     = azurerm_cognitive_account.openai.name
  sensitive = true
}

output "budget_action_group_name" {
  value = azurerm_monitor_action_group.budget_stop.name
}
