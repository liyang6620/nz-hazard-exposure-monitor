# ADR 0011: Deterministic figures, bounded prose and human approval

Status: accepted after the ten-briefing rewrite and cloud review.

## Context

Early draft briefings associated valid numbers with the wrong metrics,
invented a region name and exposed internal field names. A presence-only
numeric check could not detect these errors. The product needs short,
auditable situation notes, not model-generated measurements.

## Decision

Generate the title and key figures deterministically from that event's
published `summary.json`. The LLM may write only 2-4 situation/check
sentences, with no new numbers. Every numeric mention must match both a named
metric and its exact summary value; regions must come from the event's region
list. Reject internal field/tool names, event IDs, decimal people and missing
required limitations. Apply D8's populated-cell MMI 5.0 trigger before any
LLM call or email. A person previews by GET and makes a one-time, expiring,
HMAC-checked POST decision before any briefing becomes public.

## Consequences

The ten final fixed-event payloads passed the strict fidelity and limitations
evaluation, 10/10. Earlier drafts were superseded and their links invalidated.
The project manager approved the ten revision-3 drafts on the owner's
instruction; the owner personally approved the first cloud Kaikōura briefing.
The TEST rejection did not replace an approved public briefing. A model or
Static Maps failure cannot bypass the deterministic figures or approval gate.

See [M6 evaluation](../../evidence/m6/README.md),
[revision-3 reconciliation](../../evidence/frontend-pr1/briefing-summary-reconciliation.md),
[manual approval evidence](../../evidence/frontend-pr1/README.md), and
[Azure review evidence](../../evidence/m1-a/azure-acceptance-2026-11-02.md).
