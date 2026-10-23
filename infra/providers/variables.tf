variable "subscription_id" {
  description = "Azure subscription whose providers are registered."
  type        = string
  nullable    = false
  sensitive   = true
}

variable "already_registered" {
  description = "Required namespaces currently reported as Registered by Azure."
  type        = set(string)
  default     = []
}
