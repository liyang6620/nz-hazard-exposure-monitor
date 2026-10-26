resource "azurerm_storage_account" "data" {
  name                            = local.names.storage
  resource_group_name             = var.resource_group_name
  location                        = var.location
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  account_kind                    = "StorageV2"
  is_hns_enabled                  = true
  min_tls_version                 = "TLS1_2"
  allow_nested_items_to_be_public = false
  public_network_access_enabled   = true
  shared_access_key_enabled       = false

  blob_properties {
    delete_retention_policy {
      days = 7
    }

    container_delete_retention_policy {
      days = 7
    }
  }

  tags = var.tags
}

resource "azurerm_storage_container" "data" {
  for_each = local.blob_container_names

  name                  = each.value
  storage_account_id    = azurerm_storage_account.data.id
  container_access_type = "private"
}

resource "azurerm_storage_queue" "events" {
  name               = "events"
  storage_account_id = azurerm_storage_account.data.id
}

resource "azurerm_storage_table" "tables" {
  for_each = toset(["eventsstate", "runs", "briefings"])

  name               = each.value
  storage_account_id = azurerm_storage_account.data.id
}

resource "azurerm_storage_account_static_website" "public" {
  storage_account_id = azurerm_storage_account.data.id
  index_document     = "index.html"
  error_404_document = "404.html"
}

resource "azurerm_storage_management_policy" "data" {
  storage_account_id = azurerm_storage_account.data.id

  rule {
    name    = "raw-to-cool"
    enabled = true

    filters {
      prefix_match = ["raw/"]
      blob_types   = ["blockBlob"]
    }

    actions {
      base_blob {
        tier_to_cool_after_days_since_modification_greater_than = 30
      }
    }
  }

  rule {
    name    = "delete-curated-temporary-data"
    enabled = true

    filters {
      prefix_match = ["curated/tmp/"]
      blob_types   = ["blockBlob"]
    }

    actions {
      base_blob {
        delete_after_days_since_modification_greater_than = 7
      }
    }
  }
}

resource "azurerm_key_vault" "main" {
  name                          = local.names.key_vault
  resource_group_name           = var.resource_group_name
  location                      = var.location
  tenant_id                     = var.tenant_id
  sku_name                      = "standard"
  rbac_authorization_enabled    = true
  purge_protection_enabled      = true
  soft_delete_retention_days    = 7
  public_network_access_enabled = true
  tags                          = var.tags
}
