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
