# Terraform state bootstrap

This owner-run root creates the state storage, the empty production resource
group and one GitHub Actions user-assigned managed identity. The identity has
repository-scoped `pull_request` and `main` federated credentials. It receives
`Storage Blob Data Contributor` on the state container plus `Contributor` and
`Role Based Access Control Administrator` on the production resource group.
It receives no subscription-level role.

This root keeps local state because a backend cannot safely own the storage
that contains its own state. Keep its state encrypted and backed up outside the
repository.

No command in this directory may be applied until its saved plan is approved.
`Microsoft.Storage` and `Microsoft.ManagedIdentity` must already have been
approved and registered through `infra/providers`.

```bash
terraform init
terraform plan -out=bootstrap.tfplan
terraform show -no-color bootstrap.tfplan > bootstrap-plan.txt
```
