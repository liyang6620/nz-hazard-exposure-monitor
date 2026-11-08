# ADR 0003: Student-subscription acceptance boundaries

Status: accepted boundary, updated 9 November 2026 NZDT.

The primary deployment is Azure for Students. It must not be upgraded or given
a payment method. The student spending limit remains the final cost backstop.
This is an explicit exception to the original school-account-independence
constraint: the owner's personal Microsoft account was blocked by account
recovery controls, so production uses a school account expected to stop
working around October 2027. The Terraform and backup/migration runbook
support a fresh deployment to a later subscription; an actual migration has
not been performed.
The independent fixed-amount budgets and secure budget-stop route are deployed.
An approved direct-webhook drill proved the durable stop switch, ACS send, ARM
Function stop and owner-operated recovery. Azure rejected `Test action group`
for alert type `budget` with HTTP 409 `Free subscription not supported`.
Consequently no evidence claims that Azure Monitor delivered the Action Group
notification. The project manager later approved a separate NZD 1 November
drill budget after a one-create plan. The owner removed it on 6 Nov before a
natural alert, because an unattended stop would disrupt service. The saved
removal plan contained only that deletion; the permanent NZD 2, 5 and 8
budgets remained.

The published Azure website uses immutable data generations and a manifest
pointer. A real new GeoNet event was published 32 minutes 9 seconds after its
origin, meeting the one-hour target. The Function HTTP entrance intermittently
timed out before the handler and the owner saw one unavailable page before a
successful review-page refresh. The HMAC one-time POST approval design remains
unchanged. Operators may retry GET; they must not automate POST retries.

ArcGIS publication could not switch to Azure merely by setting a flag. The
bounded incremental publisher was subsequently reviewed, the owner placed the
server-side key in Key Vault, and the temporary vault role was removed. Azure
is now the sole enabled publisher; the local switch remains off. The hosted
item retained its ID, and its 4 Nov snapshot had 4,014 features and 3,521,464
bytes, below the 125 MiB free storage allowance. A separately approved,
queue-scoped Message Sender grant enabled a malformed-message drill. The
message entered `events-poison`, curated/gold hashes stayed unchanged, and the
grant was removed.

The natural budget alert -> Action Group -> stop path is **unverified**, not a
completed end-to-end drill. Azure for Students does not support the built-in
Action Group test; a later attended exercise needs a new reviewed plan.
A failure metric alert fired and resolved, but receipt at the first mailbox
was not observed. A second receiver was configured and another alert fired;
inbox delivery still lacks owner confirmation. D19's cost anomaly alert is
unsupported on this Free/student subscription. These are acceptance gaps, not
proof that notifications reach a person. The dated
[cost record](../cost.md) reports actual charges but cannot yet establish a
stable monthly run rate under US$3.
