# Explicit Azure resource-provider registration

This root makes D26 auditable. Its plan is reviewed and applied separately from
all resource creation. An already registered provider is imported before apply;
Terraform must not attempt to unregister providers that predate this project.

`Microsoft.AVS` is intentionally absent and remains unregistered and unmanaged
in the Azure for Students subscription. `Microsoft.Insights` is already
registered and must be imported into this root if the registration root is
adopted after approval. The first write list therefore contains seven missing
namespaces.
Every registration or import command requires normal project-manager approval.
