locals {
  function_blob_scopes = {
    raw       = azurerm_storage_container.data["raw"].id
    curated   = azurerm_storage_container.data["curated"].id
    gold      = azurerm_storage_container.data["gold"].id
    briefings = azurerm_storage_container.data["briefings"].id
    web       = "${azurerm_storage_account.data.id}/blobServices/default/containers/$web"
  }

  function_stop_role_definition_id = "/subscriptions/${var.subscription_id}/providers/Microsoft.Authorization/roleDefinitions/${uuidv5("url", "https://github.com/${var.github_repository}/roles/function-stop")}"

  github_upload_scopes = {
    curated = azurerm_storage_container.data["curated"].id
    gold    = azurerm_storage_container.data["gold"].id
    web     = "${azurerm_storage_account.data.id}/blobServices/default/containers/$web"
  }
}

resource "azurerm_role_assignment" "github_upload" {
  for_each = local.github_upload_scopes

  scope                = each.value
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = var.github_principal_id

  depends_on = [azurerm_storage_account_static_website.public]
}

resource "azurerm_role_assignment" "function_blob" {
  for_each = local.function_blob_scopes

  scope                = each.value
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_function_app_flex_consumption.main.identity[0].principal_id

  depends_on = [azurerm_storage_account_static_website.public]
}

resource "azurerm_role_assignment" "function_host_blob" {
  scope                = azurerm_storage_account.data.id
  role_definition_name = "Storage Blob Data Owner"
  principal_id         = azurerm_function_app_flex_consumption.main.identity[0].principal_id
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

resource "azurerm_role_assignment" "function_openai" {
  scope                = azurerm_cognitive_account.openai.id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = azurerm_function_app_flex_consumption.main.identity[0].principal_id
}

resource "azurerm_role_assignment" "function_stop" {
  scope              = azurerm_function_app_flex_consumption.main.id
  role_definition_id = local.function_stop_role_definition_id
  principal_id       = azurerm_function_app_flex_consumption.main.identity[0].principal_id
}
