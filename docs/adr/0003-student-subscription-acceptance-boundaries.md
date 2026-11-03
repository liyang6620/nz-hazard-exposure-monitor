# ADR 0003: Student-subscription acceptance boundaries

Status: accepted boundary, updated 4 November 2026 NZDT.

The primary deployment is Azure for Students. It must not be upgraded or given
a payment method. The student spending limit remains the final cost backstop.
The independent fixed-amount budgets and secure budget-stop route are deployed.
An approved direct-webhook drill proved the durable stop switch, ACS send, ARM
Function stop and owner-operated recovery. Azure rejected `Test action group`
for alert type `budget` with HTTP 409 `Free subscription not supported`.
Consequently no evidence claims that Azure Monitor delivered the Action Group
notification. The project manager later approved a separate NZD 1 November
drill budget after a one-create plan. It waits for a natural Cost Management
notification; its presence is not proof of Action Group delivery.

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

The one-time NZD 1 budget bound to the existing stop Action Group is waiting
for a natural Cost Management alert; it is not an accepted end-to-end drill
until the Function stops and the owner recovers it. A failure metric alert
fired and resolved, but the owner did not receive its 163 email. Receiver
configuration was enabled and no alert suppression was reported. Email
delivery remains an acceptance gap, not a proven notification path.
