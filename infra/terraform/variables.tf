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

variable "github_principal_id" {
  description = "Principal ID of the bootstrap-created GitHub managed identity. Never commit its value."
  type        = string
  nullable    = false
  sensitive   = true
}

variable "owner_object_id" {
  description = "Repository owner's Entra object ID for runs-table stop recovery. Never commit its value."
  type        = string
  nullable    = false
  sensitive   = true
}

variable "owner_poison_drill_enabled" {
  description = "Temporary events-queue sender grant for the supervised poison-message drill."
  type        = bool
  default     = false
}

variable "owner_arcgis_key_write_enabled" {
  description = "Temporary vault-scoped Secrets Officer grant for supervised ArcGIS key entry."
  type        = bool
  default     = false
}

variable "arcgis_publisher_enabled" {
  description = "Enable the single Azure ArcGIS writer only after the owner completes key handover."
  type        = bool
  default     = false
}

variable "resource_group_name" {
  description = "Production resource group pre-created by infra/bootstrap."
  type        = string
  default     = "rg-nzhem-prod"
}

variable "github_repository" {
  description = "GitHub owner/name used to derive the bootstrap-owned custom role ID."
  type        = string
  default     = "liyang6620/nz-hazard-exposure-monitor"
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

variable "failure_alert_gmail" {
  description = "Optional second recipient for the Function-failure Action Group; pass privately."
  type        = string
  default     = ""
  sensitive   = true

  validation {
    condition     = var.failure_alert_gmail == "" || can(regex("^[^@\\s]+@gmail\\.com$", var.failure_alert_gmail))
    error_message = "failure_alert_gmail must be empty or a Gmail address."
  }
}

variable "location" {
  description = "Azure region for production resources."
  type        = string
  default     = "australiaeast"
}

variable "budget_start_date" {
  description = "First day of the current billing month in RFC 3339 format."
  type        = string
  nullable    = false
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
