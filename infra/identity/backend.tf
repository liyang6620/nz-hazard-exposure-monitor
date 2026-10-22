terraform {
  backend "azurerm" {
    key              = "identity.tfstate"
    use_azuread_auth = true
    use_cli          = true
  }
}
