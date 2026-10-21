variable "subscription_id" {
  description = "Azure subscription that owns the cost-management budgets."
  type        = string
  nullable    = false
}

variable "contact_email" {
  description = "Personal email address that receives budget notifications."
  type        = string
  nullable    = false
  sensitive   = true

  validation {
    condition     = can(regex("^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$", var.contact_email))
    error_message = "contact_email must be a valid email address."
  }
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
