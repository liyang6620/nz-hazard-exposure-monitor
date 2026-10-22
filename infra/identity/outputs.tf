output "github_client_id" {
  value = azuread_application.github.client_id
}

output "github_principal_id" {
  value = azuread_service_principal.github.object_id
}

output "budget_webhook_client_id" {
  value = azuread_application.budget_webhook.client_id
}

output "budget_webhook_object_id" {
  value = azuread_application.budget_webhook.object_id
}

output "budget_webhook_identifier_uri" {
  value = azuread_application_identifier_uri.budget_webhook.identifier_uri
}
