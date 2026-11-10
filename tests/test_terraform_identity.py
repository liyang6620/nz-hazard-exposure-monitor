import json
from pathlib import Path


def test_github_oidc_uses_scoped_user_assigned_identity() -> None:
    bootstrap = Path("infra/bootstrap/main.tf").read_text(encoding="utf-8")
    plan_workflow = Path(".github/workflows/terraform-plan.yml").read_text(encoding="utf-8")
    deploy_workflow = Path(".github/workflows/deploy.yml").read_text(encoding="utf-8")
    terraform_sources = "\n".join(
        path.read_text(encoding="utf-8") for path in Path("infra").rglob("*.tf")
    )

    assert 'resource "azurerm_user_assigned_identity" "github"' in bootstrap
    assert 'repo:${local.github_subject_repository}:environment:terraform-plan"' in bootstrap
    assert 'repo:${local.github_subject_repository}:environment:production"' in bootstrap
    assert "var.github_owner_id" in bootstrap
    assert "var.github_repository_id" in bootstrap
    assert "github.event.pull_request.head.repo.full_name == github.repository" in plan_workflow
    assert "github.event.pull_request.base.ref == 'main'" in plan_workflow
    assert "github.ref == 'refs/heads/main'" in plan_workflow
    assert "github.ref == 'refs/heads/main'" in deploy_workflow
    assert 'role_definition_name = "Contributor"' in bootstrap
    assert 'role_definition_name = "Role Based Access Control Administrator"' in bootstrap
    assert 'condition_version    = "2.0"' in bootstrap
    assert "PrincipalType" in bootstrap
    assert "ServicePrincipal" in bootstrap
    assert 'resource "azurerm_role_definition" "function_stop"' in bootstrap
    assert "azuread_application" not in terraform_sources
    assert 'role_definition_name = "Owner"' not in bootstrap
    assert '"Owner"' not in bootstrap
    assert '"User Access Administrator"' not in bootstrap


def test_production_has_no_subscription_role_for_github() -> None:
    roles = Path("infra/terraform/roles.tf").read_text(encoding="utf-8")

    github_role = roles.split('resource "azurerm_role_assignment" "github_upload"')[1].split(
        'resource "', 1
    )[0]
    assert "scope                = each.value" in github_role
    assert 'role_definition_name = "Storage Blob Data Contributor"' in github_role
    assert "principal_id         = var.github_principal_id" in github_role
    assert 'scope = "/subscriptions/' not in github_role
    assert 'curated = azurerm_storage_container.data["curated"].id' in roles
    assert 'gold    = azurerm_storage_container.data["gold"].id' in roles
    assert "containers/$web" in roles
    assert "Cost Management Reader" not in roles
    assert 'resource "azurerm_role_definition"' not in roles
    assert "owner_object_id" not in github_role
    assert 'scope                = azapi_resource.tables["runs"].id' in roles
    assert "principal_id         = var.owner_object_id" in roles


def test_http_routes_use_application_authentication() -> None:
    budget = Path("infra/terraform/budget.tf").read_text(encoding="utf-8")
    function = Path("infra/terraform/function.tf").read_text(encoding="utf-8")

    assert 'resource "random_password" "budget_webhook_token"' in budget
    assert "?token=${random_password.budget_webhook_token.result}" in budget
    assert 'ip_restriction_default_action          = "Allow"' in function
    assert 'service_tag = "ActionGroup"' not in function
    assert '"BUDGET_WEBHOOK_TOKEN"' in function
    assert '"APPROVAL_TOKEN_KEY"' in function
    assert '"MAP_TOKEN_ENABLED"' in function


def test_function_data_queue_and_required_vault_setting_are_wired() -> None:
    function = Path("infra/terraform/function.tf").read_text(encoding="utf-8")
    host = Path("hosts/azure_functions/function_app.py").read_text(encoding="utf-8")
    host_config = json.loads(Path("hosts/azure_functions/host.json").read_text(encoding="utf-8"))

    assert 'connection="NZHEM_DATA_STORAGE"' in host
    assert host_config["extensionBundle"] == {
        "id": "Microsoft.Azure.Functions.ExtensionBundle",
        "version": "[4.*, 5.0.0)",
    }
    assert host_config["extensions"]["queues"]["messageEncoding"] == "none"
    assert (
        host_config["logging"]["applicationInsights"]["samplingSettings"]["excludedTypes"]
        == "Request;Exception"
    )
    assert '"NZHEM_DATA_STORAGE__queueServiceUri"' in function
    assert '"NZHEM_DATA_STORAGE__credential"' in function
    assert '"KEY_VAULT_URL"' in function
