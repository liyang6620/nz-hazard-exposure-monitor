output "required_resource_providers" {
  value = sort(tolist(local.required_resource_providers))
}
