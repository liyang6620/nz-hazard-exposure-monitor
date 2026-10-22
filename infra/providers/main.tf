locals {
  required_resource_providers = toset([
    "Microsoft.CognitiveServices",
    "Microsoft.Communication",
    "Microsoft.Insights",
    "Microsoft.KeyVault",
    "Microsoft.ManagedIdentity",
    "Microsoft.OperationalInsights",
    "Microsoft.Storage",
    "Microsoft.Web",
  ])
}

resource "azurerm_resource_provider_registration" "required" {
  for_each = local.required_resource_providers

  name = each.value

  lifecycle {
    prevent_destroy = true
  }
}

import {
  for_each = var.already_registered

  to = azurerm_resource_provider_registration.required[each.value]
  id = "/subscriptions/${var.subscription_id}/providers/${each.value}"
}
