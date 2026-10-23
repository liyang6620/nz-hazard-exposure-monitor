variable "subscription_id" {
  description = "Azure subscription used by the OIDC workload identity."
  type        = string
  nullable    = false
  sensitive   = true
}

variable "tenant_id" {
  description = "Microsoft Entra tenant for workload identities."
  type        = string
  nullable    = false
  sensitive   = true
}

variable "github_repository" {
  description = "GitHub owner/name used in federated credential subjects."
  type        = string
  default     = "liyang6620/nz-hazard-exposure-monitor"
}

variable "tfstate_resource_group_name" {
  description = "Resource group emitted by infra/bootstrap."
  type        = string
  nullable    = false
}

variable "tfstate_storage_account_name" {
  description = "Storage account emitted by infra/bootstrap."
  type        = string
  nullable    = false
}
