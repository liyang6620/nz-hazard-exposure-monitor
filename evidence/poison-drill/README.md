# Supervised poison-message drill

The project manager approved a temporary `Storage Queue Data Message Sender`
grant for the repository owner scoped only to the `events` queue. The Terraform
switch defaults to false. Its enabled plan must show only one role assignment
creation; the post-drill plan must show only that assignment's deletion. The
Function retains its existing queue and table roles.

The saved production plan in ignored `tmp/` has exactly one creation, zero
updates and zero deletions; the role scope ends in `/queues/events`. The owner
is not granted a data-reader role on `events-poison`. When the owner is present,
capture a pre-injection gold hash, enable the narrow grant, then have the owner
inject one malformed JSON message into `events`. Observe the Function retry
count, host poison-transfer log and existing Function exception alert. A
message is never read back into public evidence. Repeat the gold hash and
confirm it is identical.
Remove the temporary grant immediately and verify its absence in Terraform
state. Azure resource names, owner identity and message content are kept out
of committed evidence and terminal transcripts.
