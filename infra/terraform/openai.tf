resource "azurerm_cognitive_account" "openai" {
  name                          = local.names.openai
  resource_group_name           = azurerm_resource_group.production.name
  location                      = azurerm_resource_group.production.location
  kind                          = "OpenAI"
  sku_name                      = "S0"
  custom_subdomain_name         = local.names.openai
  local_auth_enabled            = false
  public_network_access_enabled = true
  tags                          = var.tags
}

resource "azurerm_cognitive_deployment" "gpt_5_mini" {
  name                   = "gpt-5-mini"
  cognitive_account_id   = azurerm_cognitive_account.openai.id
  version_upgrade_option = "OnceNewDefaultVersionAvailable"

  model {
    format  = "OpenAI"
    name    = "gpt-5-mini"
    version = var.azure_openai_model_version
  }

  sku {
    name     = "GlobalStandard"
    capacity = 1
  }
}
