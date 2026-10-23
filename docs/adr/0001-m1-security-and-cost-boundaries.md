# ADR 0001: M1 security and cost boundaries

## Status

Accepted for plan review, 2026-10-23.

## Context

M1 must deploy one low-cost Function App, protect it with a durable budget stop,
and permit GitHub to plan and deploy without a stored Azure credential. Public
network endpoints are necessary to stay within the USD 3 monthly ceiling.

## Decision

- Use one Linux Flex Consumption FC1 plan with Python 3.12, 2 GB memory, one
  maximum instance, and no always-ready instances.
- Use public Azure endpoints with TLS, Entra authorization, RBAC, and disabled
  storage anonymous access. Private endpoints are excluded because their fixed
  costs conflict with C1.
- Give the Function a system-assigned identity for runtime access. A separate
  user-assigned identity is limited to the deployment package container because
  Flex requires the package identity before the Function's system identity
  exists.
- Protect `budget_stop` with Function Easy Auth and an Entra audience
  application. The budget Action Group uses an AAD-authenticated secure webhook;
  no function key is stored.
- Use separate Action Groups. Function exceptions send email only; budget
  exhaustion sends email and invokes `budget_stop`. Reusing one group would stop
  production for an ordinary application failure.
- Give the Function a custom role containing only `Microsoft.Web/sites/read`
  and `Microsoft.Web/sites/stop/action`, assigned at the one Function App.
- GitHub uses repository- and branch-scoped OIDC federated credentials. It can
  read the resource group and costs, deploy the Function, write only the package
  container, and read only run telemetry. It cannot run Terraform apply.
- Azure OpenAI local-key authentication is disabled. The deployment is
  `gpt-5-mini` Global Standard with capacity 1 and runtime limits of minimal
  reasoning, 1,200 maximum output tokens, 12,000 total reserved tokens per
  briefing, and 10 briefings per month.

## Consequences

The public endpoints increase exposure compared with private networking, so
authentication and least-privilege RBAC are mandatory. Global Standard may
process public earthquake and exposure data outside Australia. There are two
no-charge Action Groups because a shared webhook group would create an unsafe
failure mode. The first deployment needs owner-run identity and infrastructure
plans before OIDC can take over CI planning and code deployment.
