locals {
  function_blob_scopes = {
    raw       = azurerm_storage_container.data["raw"].id
    curated   = azurerm_storage_container.data["curated"].id
    gold      = azurerm_storage_container.data["gold"].id
    briefings = azurerm_storage_container.data["briefings"].id
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
  scope       = "/subscriptions/${var.subscription_id}/resourceGroups/${var.resource_group_name}"
  description = "May read and stop only the NZHEM Function App."

  permissions {
    actions = [
      "Microsoft.Web/sites/read",
      "Microsoft.Web/sites/stop/action",
    ]
    not_actions = []
  }

  assignable_scopes = ["/subscriptions/${var.subscription_id}/resourceGroups/${var.resource_group_name}"]
}

resource "azurerm_role_assignment" "function_stop" {
  scope              = azurerm_function_app_flex_consumption.main.id
  role_definition_id = azurerm_role_definition.function_stop.role_definition_resource_id
  principal_id       = azurerm_function_app_flex_consumption.main.identity[0].principal_id
}

resource "azurerm_role_assignment" "owner_gold_reader" {
  scope                = azurerm_storage_container.data["gold"].id
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = var.owner_object_id
}

resource "azurerm_role_assignment" "owner_killswitch_operator" {
  scope                = azurerm_storage_account.data.id
  role_definition_name = "Storage Table Data Contributor"
  principal_id         = var.owner_object_id
}
