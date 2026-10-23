terraform {
  backend "azurerm" {
    key              = "guardrails.tfstate"
    use_azuread_auth = true
    use_cli          = true
  }
}
