variable "subscription_id" {
  description = "Azure subscription that owns the Terraform state resources."
  type        = string
  nullable    = false
  sensitive   = true
}

variable "location" {
  description = "Azure region for the Terraform state resources."
  type        = string
  default     = "australiaeast"
}

variable "production_resource_group_name" {
  description = "Pre-created resource group that contains all production resources and deployment RBAC."
  type        = string
  default     = "rg-nzhem-prod"
}

variable "github_repository" {
  description = "GitHub owner/name used in the workload identity subjects."
  type        = string
  default     = "liyang6620/nz-hazard-exposure-monitor"
}

variable "owner_object_id" {
  description = "Entra object ID of the owner who operates remote state."
  type        = string
  nullable    = false
  sensitive   = true
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
