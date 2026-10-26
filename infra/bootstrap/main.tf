locals {
  suffix = substr(sha256(var.subscription_id), 0, 8)

  delegated_role_names = toset([
    "Cognitive Services OpenAI User",
    "Key Vault Secrets User",
    "Storage Blob Data Contributor",
    "Storage Queue Data Contributor",
    "Storage Table Data Contributor",
  ])

  delegated_role_definition_ids = concat(
    [for role in data.azurerm_role_definition.delegated : basename(role.role_definition_id)],
    [basename(azurerm_role_definition.function_stop.role_definition_id)],
  )

  github_rbac_condition = <<-CONDITION
    (
      (!(ActionMatches{'Microsoft.Authorization/roleAssignments/write'}))
      OR
      (
        @Request[Microsoft.Authorization/roleAssignments:RoleDefinitionId] ForAnyOfAnyValues:GuidEquals {${join(", ", local.delegated_role_definition_ids)}}
        AND
        @Request[Microsoft.Authorization/roleAssignments:PrincipalType] ForAnyOfAnyValues:StringEqualsIgnoreCase {'ServicePrincipal'}
      )
    )
    AND
    (
      (!(ActionMatches{'Microsoft.Authorization/roleAssignments/delete'}))
      OR
      (
        @Resource[Microsoft.Authorization/roleAssignments:RoleDefinitionId] ForAnyOfAnyValues:GuidEquals {${join(", ", local.delegated_role_definition_ids)}}
        AND
        @Resource[Microsoft.Authorization/roleAssignments:PrincipalType] ForAnyOfAnyValues:StringEqualsIgnoreCase {'ServicePrincipal'}
      )
    )
  CONDITION
}

data "azurerm_role_definition" "delegated" {
  for_each = local.delegated_role_names
  name     = each.value
  scope    = "/subscriptions/${var.subscription_id}"
}

resource "azurerm_resource_group" "state" {
  name     = "rg-nzhem-tfstate"
  location = var.location
  tags     = var.tags
}

resource "azurerm_resource_group" "production" {
  name     = var.production_resource_group_name
  location = var.location
  tags     = var.tags
}

resource "azurerm_storage_account" "state" {
  name                            = "stnzhemtf${local.suffix}"
  resource_group_name             = azurerm_resource_group.state.name
  location                        = azurerm_resource_group.state.location
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  min_tls_version                 = "TLS1_2"
  allow_nested_items_to_be_public = false
  shared_access_key_enabled       = false

  blob_properties {
    versioning_enabled = true

    delete_retention_policy {
      days = 14
    }

    container_delete_retention_policy {
      days = 14
    }
  }

  tags = var.tags
}

resource "azurerm_storage_container" "state" {
  name                  = "tfstate"
  storage_account_id    = azurerm_storage_account.state.id
  container_access_type = "private"
}

resource "azurerm_role_assignment" "owner_state" {
  scope                = azurerm_storage_container.state.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = var.owner_object_id
}

resource "azurerm_user_assigned_identity" "github" {
  name                = "id-nzhem-github"
  resource_group_name = azurerm_resource_group.production.name
  location            = azurerm_resource_group.production.location
  tags                = var.tags
}

resource "azurerm_role_definition" "function_stop" {
  name               = "NZHEM Function Stop Operator"
  role_definition_id = uuidv5("url", "https://github.com/${var.github_repository}/roles/function-stop")
  scope              = azurerm_resource_group.production.id
  description        = "May read and stop only the NZHEM Function App."

  permissions {
    actions = [
      "Microsoft.Web/sites/read",
      "Microsoft.Web/sites/stop/action",
    ]
    not_actions = []
  }

  assignable_scopes = [azurerm_resource_group.production.id]
}

resource "azurerm_federated_identity_credential" "github_pull_request" {
  name                      = "github-pull-request-plan"
  user_assigned_identity_id = azurerm_user_assigned_identity.github.id
  audience                  = ["api://AzureADTokenExchange"]
  issuer                    = "https://token.actions.githubusercontent.com"
  subject                   = "repo:${var.github_repository}:pull_request"
}

resource "azurerm_federated_identity_credential" "github_main" {
  name                      = "github-main-deploy"
  user_assigned_identity_id = azurerm_user_assigned_identity.github.id
  audience                  = ["api://AzureADTokenExchange"]
  issuer                    = "https://token.actions.githubusercontent.com"
  subject                   = "repo:${var.github_repository}:ref:refs/heads/main"
}

resource "azurerm_role_assignment" "github_state" {
  scope                = azurerm_storage_container.state.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.github.principal_id
}

resource "azurerm_role_assignment" "github_production_contributor" {
  scope                = azurerm_resource_group.production.id
  role_definition_name = "Contributor"
  principal_id         = azurerm_user_assigned_identity.github.principal_id
}

resource "azurerm_role_assignment" "github_production_rbac" {
  scope                = azurerm_resource_group.production.id
  role_definition_name = "Role Based Access Control Administrator"
  principal_id         = azurerm_user_assigned_identity.github.principal_id
  condition            = local.github_rbac_condition
  condition_version    = "2.0"
}
