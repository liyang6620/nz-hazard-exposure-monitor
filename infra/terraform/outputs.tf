output "resource_group_name" {
  value = azurerm_resource_group.production.name
}

output "storage_account_name" {
  value = azurerm_storage_account.data.name
}

output "function_app_name" {
  value = azurerm_function_app_flex_consumption.main.name
}

output "function_app_default_hostname" {
  value = azurerm_function_app_flex_consumption.main.default_hostname
}

output "key_vault_name" {
  value = azurerm_key_vault.main.name
}

output "azure_openai_account_name" {
  value = azurerm_cognitive_account.openai.name
}

output "budget_action_group_name" {
  value = azurerm_monitor_action_group.budget_stop.name
}
