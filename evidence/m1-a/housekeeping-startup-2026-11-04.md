# Azure housekeeping startup correction, 4 Nov 2026 NZDT

PR [#53](https://github.com/liyang6620/nz-hazard-exposure-monitor/pull/53)
changed only the Azure timer binding to `run_on_startup=False` and corrected
the runbook. All nine PR CI checks and the merged main-branch CI passed.

The Flex Function was deployed from the immutable CI artifact for main commit
`9abbf6c215323b0b342367e9fc8d3b35fb8f5bef` using Functions Core Tools
`func azure functionapp publish --no-build --python --force`. The deployment
pipeline and host health check completed at 22:21:45 UTC on 3 Nov. The
token-free invalid review GET returned that exact `X-NZHEM-Build` value, and
all six expected triggers were indexed.

Before and after deployment, the base `AzureWebJobsStorage` setting was absent,
`AzureWebJobsStorage__credential` was `managedidentity`, the host account name
was present, and `HOUSEKEEPING_SCHEDULE` was `0 0 * * * *`. No app setting or
Terraform resource was changed. The public manifest was generated at 22:00
UTC before the deployment and had not been republished by the deployment
itself. An initial Application Insights query found no housekeeping request
between 22:20 and 22:40 UTC, consistent with startup execution being disabled.

The next scheduled 23:00 UTC request was recorded successful at
23:00:00.018 UTC. The public manifest advanced from 22:00 to 23:00:02 UTC,
and all six triggers remained indexed. Application Insights returned no
housekeeping request between the 22:21 deployment and 23:00; the only request
in that interval's query was the scheduled 23:00 run. This passes the
post-deployment publication gate and confirms the extra startup pass was
absent in the observed window.

An attempt to send a test notification from the existing Function-failure
Action Group using Azure Monitor's metric-static-threshold test endpoint
returned HTTP 409 `Free subscription not supported`. This changed no resource
or receiver. The owner requested a repeat check of the current 163 recipient
before considering another mailbox; Action Group mail delivery remains
unverified.

For the repeat check, a saved targeted Terraform plan contained exactly one
creation: `Storage Queue Data Message Sender` for the owner on the `events`
queue. The plan's scope, role and principal were checked before apply. One
`invalid-json` message was sent; the queue trigger logged failed requests,
and the `events-poison` approximate count rose from 25 to 26. The
`nzhem-function-execution-failure` alert entered Fired at 22:41:47 UTC with
no suppression. Gold blob inventory contained 42 objects before and after;
the SHA-256 of sorted name, size and ETag records was unchanged:
`5DBB550974E97ACE6836269DED2C18323EAF9E8888536F1B121A0F09CA926737`.
This is a metadata identity check, not a fresh content-byte hash. The
temporary role was immediately removed by a saved plan with exactly one
deletion; Terraform state and an Azure role-scope query both showed it absent.
The owner checked the 163 inbox and spam and reported no alert email. The
owner then requested a Gmail second receiver for the existing failure Action
Group; that change and its own delivery check are separate from this drill.
