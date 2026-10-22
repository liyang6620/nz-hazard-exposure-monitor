# Terraform state bootstrap

This owner-run root creates the storage used by the other Terraform roots. It
keeps local state because a backend cannot safely own the storage that contains
its own state. Keep its state encrypted and backed up outside the repository.

No command in this directory may be applied until its saved plan is approved.
`Microsoft.Storage` must already have been approved and registered through
`infra/providers`.

```bash
terraform init
terraform plan -out=bootstrap.tfplan
terraform show -no-color bootstrap.tfplan > bootstrap-plan.txt
```
