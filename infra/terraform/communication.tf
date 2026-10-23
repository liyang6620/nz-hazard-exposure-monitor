resource "azurerm_communication_service" "main" {
  name                = local.names.communication
  resource_group_name = azurerm_resource_group.production.name
  data_location       = "Australia"
  tags                = var.tags
}

resource "azurerm_email_communication_service" "main" {
  name                = local.names.email
  resource_group_name = azurerm_resource_group.production.name
  data_location       = "Australia"
  tags                = var.tags
}

resource "azurerm_email_communication_service_domain" "managed" {
  name                             = "AzureManagedDomain"
  email_service_id                 = azurerm_email_communication_service.main.id
  domain_management                = "AzureManaged"
  user_engagement_tracking_enabled = false
  tags                             = var.tags
}

resource "azurerm_communication_service_email_domain_association" "main" {
  communication_service_id = azurerm_communication_service.main.id
  email_service_domain_id  = azurerm_email_communication_service_domain.managed.id
}
