output "resource_group_name" {
  value = azurerm_resource_group.state.name
}

output "storage_account_name" {
  value     = azurerm_storage_account.state.name
  sensitive = true
}

output "container_name" {
  value = azurerm_storage_container.state.name
}

output "production_resource_group_name" {
  value = azurerm_resource_group.production.name
}

output "github_client_id" {
  value = azurerm_user_assigned_identity.github.client_id
}

output "github_principal_id" {
  value = azurerm_user_assigned_identity.github.principal_id
}

output "function_stop_role_definition_id" {
  value = azurerm_role_definition.function_stop.role_definition_resource_id
}
