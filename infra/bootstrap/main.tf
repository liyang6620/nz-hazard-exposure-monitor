locals {
  suffix = substr(sha256(var.subscription_id), 0, 8)
}

resource "azurerm_resource_group" "state" {
  name     = "rg-nzhem-tfstate"
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
  scope                = azurerm_storage_container.state.resource_manager_id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = var.owner_object_id
}
