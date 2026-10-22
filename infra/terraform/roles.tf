locals {
  function_blob_scopes = {
    raw       = azurerm_storage_container.data["raw"].resource_manager_id
    curated   = azurerm_storage_container.data["curated"].resource_manager_id
    gold      = azurerm_storage_container.data["gold"].resource_manager_id
    briefings = azurerm_storage_container.data["briefings"].resource_manager_id
    web       = "${azurerm_storage_account.data.id}/blobServices/default/containers/$web"
  }
}

resource "azurerm_role_assignment" "function_blob" {
  for_each = local.function_blob_scopes

  scope                = each.value
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_function_app_flex_consumption.main.identity[0].principal_id

  depends_on = [azurerm_storage_account_static_website.public]
}

resource "azurerm_role_assignment" "function_queue" {
  scope                = azurerm_storage_account.data.id
  role_definition_name = "Storage Queue Data Contributor"
  principal_id         = azurerm_function_app_flex_consumption.main.identity[0].principal_id
}

resource "azurerm_role_assignment" "function_table" {
  scope                = azurerm_storage_account.data.id
  role_definition_name = "Storage Table Data Contributor"
  principal_id         = azurerm_function_app_flex_consumption.main.identity[0].principal_id
}

resource "azurerm_role_assignment" "function_key_vault" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_function_app_flex_consumption.main.identity[0].principal_id
}

resource "azurerm_role_assignment" "function_email" {
  scope                = azurerm_communication_service.main.id
  role_definition_name = "Azure Communication Services Email Sender"
  principal_id         = azurerm_function_app_flex_consumption.main.identity[0].principal_id
}

resource "azurerm_role_assignment" "function_openai" {
  scope                = azurerm_cognitive_account.openai.id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = azurerm_function_app_flex_consumption.main.identity[0].principal_id
}

resource "azurerm_role_definition" "function_stop" {
  name        = "NZHEM Function Stop Operator"
  scope       = azurerm_resource_group.production.id
  description = "May read and stop only the NZHEM Function App."

  permissions {
    actions = [
      "Microsoft.Web/sites/read",
      "Microsoft.Web/sites/stop/action",
    ]
    not_actions = []
  }

  assignable_scopes = [azurerm_resource_group.production.id]
}

resource "azurerm_role_assignment" "function_stop" {
  scope              = azurerm_function_app_flex_consumption.main.id
  role_definition_id = azurerm_role_definition.function_stop.role_definition_resource_id
  principal_id       = azurerm_function_app_flex_consumption.main.identity[0].principal_id
}

resource "azurerm_role_assignment" "owner_gold_reader" {
  scope                = azurerm_storage_container.data["gold"].resource_manager_id
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = var.owner_object_id
}

resource "azurerm_role_assignment" "owner_killswitch_operator" {
  scope                = azurerm_storage_account.data.id
  role_definition_name = "Storage Table Data Contributor"
  principal_id         = var.owner_object_id
}

resource "azurerm_role_assignment" "github_reader" {
  scope                = azurerm_resource_group.production.id
  role_definition_name = "Reader"
  principal_id         = var.github_principal_id
}

resource "azurerm_role_assignment" "github_website_deployer" {
  scope                = azurerm_function_app_flex_consumption.main.id
  role_definition_name = "Website Contributor"
  principal_id         = var.github_principal_id
}

resource "azurerm_role_assignment" "github_package_storage" {
  scope                = azurerm_storage_container.data["deployments"].resource_manager_id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = var.github_principal_id
}

resource "azurerm_role_assignment" "github_runlog_reader" {
  scope                = azurerm_storage_account.data.id
  role_definition_name = "Storage Table Data Reader"
  principal_id         = var.github_principal_id
}

resource "azurerm_role_assignment" "github_cost_reader" {
  scope                = "/subscriptions/${var.subscription_id}"
  role_definition_name = "Cost Management Reader"
  principal_id         = var.github_principal_id
}
