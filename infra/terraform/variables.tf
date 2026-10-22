variable "subscription_id" {
  description = "Production Azure subscription. Never commit its value."
  type        = string
  nullable    = false
  sensitive   = true
}

variable "tenant_id" {
  description = "Production Microsoft Entra tenant. Never commit its value."
  type        = string
  nullable    = false
  sensitive   = true
}

variable "owner_object_id" {
  description = "Entra object ID of the repository owner for local Power BI reads."
  type        = string
  nullable    = false
  sensitive   = true
}

variable "notification_email" {
  description = "Personal address for operational, failure and budget alerts."
  type        = string
  nullable    = false
  sensitive   = true

  validation {
    condition     = can(regex("^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$", var.notification_email))
    error_message = "notification_email must be a valid email address."
  }
}

variable "github_principal_id" {
  description = "Service principal object ID emitted by infra/identity."
  type        = string
  nullable    = false
  sensitive   = true
}

variable "budget_webhook_client_id" {
  description = "Application client ID used by Function Easy Auth."
  type        = string
  nullable    = false
  sensitive   = true
}

variable "budget_webhook_object_id" {
  description = "Application object ID used by the secure Action Group webhook."
  type        = string
  nullable    = false
  sensitive   = true
}

variable "budget_webhook_identifier_uri" {
  description = "Audience URI emitted by infra/identity."
  type        = string
  nullable    = false
  sensitive   = true
}

variable "location" {
  description = "Azure region for production resources."
  type        = string
  default     = "australiaeast"
}

variable "budget_start_date" {
  description = "First day of the current billing month in RFC 3339 format."
  type        = string
  default     = "2026-10-01T00:00:00Z"
}

variable "budget_end_date" {
  description = "Budget expiry date in RFC 3339 format."
  type        = string
  default     = "2036-10-01T00:00:00Z"
}

variable "azure_openai_model_version" {
  description = "Azure model version verified immediately before apply."
  type        = string
  default     = "2025-08-07"
}

variable "tags" {
  description = "Common resource tags."
  type        = map(string)
  default = {
    application = "nz-hazard-exposure-monitor"
    environment = "production"
    managed-by  = "terraform"
  }
}
