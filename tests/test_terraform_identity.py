from pathlib import Path


def test_github_oidc_uses_scoped_user_assigned_identity() -> None:
    bootstrap = Path("infra/bootstrap/main.tf").read_text(encoding="utf-8")
    terraform_sources = "\n".join(
        path.read_text(encoding="utf-8") for path in Path("infra").rglob("*.tf")
    )

    assert 'resource "azurerm_user_assigned_identity" "github"' in bootstrap
    assert 'subject                   = "repo:${var.github_repository}:pull_request"' in bootstrap
    assert (
        'subject                   = "repo:${var.github_repository}:ref:refs/heads/main"'
        in bootstrap
    )
    assert 'role_definition_name = "Contributor"' in bootstrap
    assert 'role_definition_name = "Role Based Access Control Administrator"' in bootstrap
    assert "azuread_application" not in terraform_sources
    assert 'role_definition_name = "Owner"' not in bootstrap


def test_production_has_no_subscription_role_for_github() -> None:
    roles = Path("infra/terraform/roles.tf").read_text(encoding="utf-8")

    assert "github_principal_id" not in roles
    assert "Cost Management Reader" not in roles


def test_budget_webhook_is_token_and_network_restricted() -> None:
    budget = Path("infra/terraform/budget.tf").read_text(encoding="utf-8")
    function = Path("infra/terraform/function.tf").read_text(encoding="utf-8")

    assert 'resource "random_password" "budget_webhook_token"' in budget
    assert "?token=${random_password.budget_webhook_token.result}" in budget
    assert 'ip_restriction_default_action          = "Deny"' in function
    assert 'service_tag = "ActionGroup"' in function
    assert '"BUDGET_WEBHOOK_TOKEN"' in function
