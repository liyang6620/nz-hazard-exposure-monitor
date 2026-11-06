# Unchanged-data publication deployment, 6 Nov 2026

PR #62 merged the unchanged-data skip, three-generation retention and separate
hourly housekeeping heartbeat. The manually dispatched GitHub deployment for
merge commit `08efe7441656f0ad01b96ff2c87cfc5d1c1b4164` was skipped because
the repository's `AZURE_DEPLOYMENT_ENABLED` variable was not `true`.

The already approved CI Function package for that exact commit was downloaded
from the successful main CI run. Its embedded `build_git_sha.txt` matched the
commit and the ZIP was 180,808,013 bytes, below the one-GB limit. It was
deployed locally with the runbook's Flex-supported `func azure functionapp
publish --no-build --python --force` path, without a Terraform apply, resource
or permission change. Deployment began at 00:34:40 UTC and the Flex deployment
pipeline reported success at 00:36:54 UTC.

Immediately after deployment, the HTTP build header changed from
`9abbf6c215323b0b342367e9fc8d3b35fb8f5bef` to
`08efe7441656f0ad01b96ff2c87cfc5d1c1b4164`. Azure indexed six functions:
`budget_stop`, `housekeeping`, `map_token`, `process_event`,
`review_briefing_get` and `review_briefing_post`. The exact legacy
`AzureWebJobsStorage` setting remained absent; only
`AzureWebJobsStorage__accountName` and
`AzureWebJobsStorage__credential=managedidentity` were present. The host
health endpoint reported Running. Before the first scheduled run, the public
manifest showed a 00:00:19 UTC generation.

The first scheduled post-deployment invocation at 01:00 UTC failed after
19.6 seconds. Application Insights recorded `DirectoryIsNotEmpty` in
`AzureDataWorkspace.prune_web_generations`: Azure ADLS Gen2 rejected deleting a
directory marker before its contained blobs. The data manifest was updated
before the exception, but `/data/housekeeping.json` remained absent. This is a
failed run, not proof of hourly health.

The follow-up fix uses ADLS Gen2's recursive directory delete and limits timer
cleanup to one stale generation per run. A separate bounded one-time cleanup
removed 241 old public generations while preserving the active generation and
newest three versions; the post-cleanup listing found exactly three. The fix
has regression tests for invisible directory markers and the per-run bound.
The next successful scheduled request and heartbeat remain acceptance gates.
An unchanged manifest is expected
when no event, briefing or other public data changed; the heartbeat and run
record, not manifest age, establish hourly health.
