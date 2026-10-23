terraform {
  required_version = ">= 1.8.0"

  required_providers {
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 3.5"
    }
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.81"
    }
  }
}

provider "azuread" {
  tenant_id = var.tenant_id
}

provider "azurerm" {
  features {}

  subscription_id                 = var.subscription_id
  tenant_id                       = var.tenant_id
  resource_provider_registrations = "none"
}
