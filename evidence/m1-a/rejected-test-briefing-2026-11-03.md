# Rejected cloud test briefing

On 3 Nov 2026 (NZDT), the repository owner reported personally using the
browser GET confirmation page and POST Reject button for test event
`2026p824047`. A read-only request to the public site's current manifest
(`20261102T110000353521Z`) and this event's `summary.json` returned
`briefing.status = rejected` and `briefing.public_path = null`. A direct HEAD
request for `/briefings/2026p824047.html` returned HTTP 404. Thus the
rejection is reflected in the published data and no public briefing file is
available. No script submitted the decision.

The private Azure Table row was not read because the owner identity has no
briefings-table data role. The public result and the owner's first-hand
confirmation are the available evidence; do not describe the private row as
independently checked.
