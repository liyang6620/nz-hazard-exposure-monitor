output "budget_ids" {
  description = "Subscription budget resource IDs keyed by budget name."
  value = {
    spend-alert-1 = azurerm_consumption_budget_subscription.spend_alert_1.id
    spend-alert-3 = azurerm_consumption_budget_subscription.spend_alert_3.id
    spend-alert-5 = azurerm_consumption_budget_subscription.spend_alert_5.id
  }
}
