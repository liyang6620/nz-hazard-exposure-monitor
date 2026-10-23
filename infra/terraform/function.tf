resource "azurerm_user_assigned_identity" "package_storage" {
  name                = "id-nzhem-package-storage"
  resource_group_name = azurerm_resource_group.production.name
  location            = azurerm_resource_group.production.location
  tags                = var.tags
}

resource "azurerm_role_assignment" "package_storage_blob" {
  scope                = azurerm_storage_container.data["deployments"].resource_manager_id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.package_storage.principal_id
}

resource "azurerm_service_plan" "function" {
  name                = local.names.service_plan
  resource_group_name = azurerm_resource_group.production.name
  location            = azurerm_resource_group.production.location
  os_type             = "Linux"
  sku_name            = "FC1"
  tags                = var.tags
}

resource "azurerm_function_app_flex_consumption" "main" {
  name                = local.names.function_app
  resource_group_name = azurerm_resource_group.production.name
  location            = azurerm_resource_group.production.location
  service_plan_id     = azurerm_service_plan.function.id

  runtime_name                  = "python"
  runtime_version               = "3.12"
  instance_memory_in_mb         = 2048
  maximum_instance_count        = 1
  http_concurrency              = 1
  https_only                    = true
  public_network_access_enabled = true

  storage_container_type                         = "blobContainer"
  storage_container_endpoint                     = "${azurerm_storage_account.data.primary_blob_endpoint}${azurerm_storage_container.data["deployments"].name}"
  storage_authentication_type                    = "UserAssignedIdentity"
  storage_user_assigned_identity_id              = azurerm_user_assigned_identity.package_storage.id
  webdeploy_publish_basic_authentication_enabled = false

  identity {
    type         = "SystemAssigned, UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.package_storage.id]
  }

  auth_settings_v2 {
    auth_enabled           = true
    require_authentication = true
    require_https          = true
    unauthenticated_action = "Return401"
    default_provider       = "azureactivedirectory"

    active_directory_v2 {
      client_id            = var.budget_webhook_client_id
      tenant_auth_endpoint = "https://login.microsoftonline.com/${var.tenant_id}/v2.0"
      allowed_audiences    = [var.budget_webhook_identifier_uri]
    }

    login {
      token_store_enabled = false
    }
  }

  site_config {
    application_insights_connection_string = azurerm_application_insights.main.connection_string
    minimum_tls_version                    = "1.2"
    scm_minimum_tls_version                = "1.2"
    http2_enabled                          = true
  }

  app_settings = {
    "APPLICATIONINSIGHTS_CONNECTION_STRING" = azurerm_application_insights.main.connection_string
    "AzureWebJobsStorage__accountName"      = azurerm_storage_account.data.name
    "AzureWebJobsStorage__credential"       = "managedidentity"
    "FUNCTIONS_WORKER_RUNTIME"              = "python"
    "HOUSEKEEPING_SCHEDULE"                 = "0 0 * * * *"
    "POLL_INTERVAL_MINUTES"                 = "60"
    "STORAGE_ACCOUNT_NAME"                  = azurerm_storage_account.data.name
    "AZURE_SUBSCRIPTION_ID"                 = var.subscription_id
    "AZURE_RESOURCE_GROUP"                  = azurerm_resource_group.production.name
    "AZURE_FUNCTION_APP_NAME"               = local.names.function_app
    "ACS_ENDPOINT"                          = "https://${azurerm_communication_service.main.hostname}"
    "ACS_SENDER"                            = "DoNotReply@${azurerm_email_communication_service_domain.managed.from_sender_domain}"
    "NOTIFICATION_EMAIL"                    = var.notification_email
    "AZURE_OPENAI_ENDPOINT"                 = azurerm_cognitive_account.openai.endpoint
    "AZURE_OPENAI_DEPLOYMENT"               = azurerm_cognitive_deployment.gpt_5_mini.name
    "LLM_REASONING_EFFORT"                  = "minimal"
    "LLM_MAX_OUTPUT_TOKENS"                 = "1200"
    "BRIEFING_TOTAL_TOKEN_LIMIT"            = "12000"
    "BRIEFING_MONTHLY_LIMIT"                = "10"
  }

  depends_on = [azurerm_role_assignment.package_storage_blob]
  tags       = var.tags
}
