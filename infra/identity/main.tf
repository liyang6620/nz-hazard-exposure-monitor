data "azuread_client_config" "current" {}

resource "azuread_application" "github" {
  display_name     = "nzhem-github-oidc"
  sign_in_audience = "AzureADMyOrg"
  owners           = [data.azuread_client_config.current.object_id]
}

resource "azuread_service_principal" "github" {
  client_id                    = azuread_application.github.client_id
  app_role_assignment_required = false
  owners                       = [data.azuread_client_config.current.object_id]
}

resource "azuread_application_federated_identity_credential" "pull_request" {
  application_id = azuread_application.github.id
  display_name   = "github-pull-request-plan"
  description    = "Terraform plans from pull requests in the public repository."
  audiences      = ["api://AzureADTokenExchange"]
  issuer         = "https://token.actions.githubusercontent.com"
  subject        = "repo:${var.github_repository}:pull_request"
}

resource "azuread_application_federated_identity_credential" "main" {
  application_id = azuread_application.github.id
  display_name   = "github-main-deploy"
  description    = "Function package deployment from the protected main branch."
  audiences      = ["api://AzureADTokenExchange"]
  issuer         = "https://token.actions.githubusercontent.com"
  subject        = "repo:${var.github_repository}:ref:refs/heads/main"
}

resource "azuread_application" "budget_webhook" {
  display_name     = "nzhem-budget-webhook"
  sign_in_audience = "AzureADMyOrg"
  owners           = [data.azuread_client_config.current.object_id]

  api {
    requested_access_token_version = 2
  }
}

resource "azuread_application_identifier_uri" "budget_webhook" {
  application_id = azuread_application.budget_webhook.id
  identifier_uri = "api://${azuread_application.budget_webhook.client_id}"
}

resource "azuread_service_principal" "budget_webhook" {
  client_id                    = azuread_application.budget_webhook.client_id
  app_role_assignment_required = false
  owners                       = [data.azuread_client_config.current.object_id]
}

resource "azurerm_role_assignment" "github_state" {
  scope                = "/subscriptions/${var.subscription_id}/resourceGroups/${var.tfstate_resource_group_name}/providers/Microsoft.Storage/storageAccounts/${var.tfstate_storage_account_name}/blobServices/default/containers/tfstate"
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azuread_service_principal.github.object_id
}
