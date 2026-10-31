# Retired identity root

This root was retired when the production target moved to an Azure for Students
subscription whose school directory blocks application registration.

The GitHub workload identity is now an Azure user-assigned managed identity in
`infra/bootstrap`. Its federated credentials do not require an Entra
application registration. Keeping the identity in bootstrap also avoids a
deployment-order cycle: the owner creates the reviewed bootstrap resources,
then GitHub can authenticate to the remote backend and production resource
group without a stored secret.

Do not initialize or apply this directory.
