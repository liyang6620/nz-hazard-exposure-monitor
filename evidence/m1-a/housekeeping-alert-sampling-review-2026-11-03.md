# Monitoring correction for project-manager review

The emergency missing-housekeeping alert was created under the one-resource
preapproval, but it counts `AppRequests` for a function that runs only hourly.
Application Insights is configured to sample 20% of telemetry. Azure `runs`
records and the public manifest prove successful 23:00Z and 00:00Z runs;
the `AppRequests` query still returned zero rows for that period. The alert
could therefore mail a false outage notification while the site is current.
Its creation alone does not close the monitoring acceptance item.

Proposed correction: set this project's existing Application Insights
`sampling_percentage` from 20 to 100. The private saved plan at
`tmp/housekeeping-sampling-review.tfplan` contains **one update** to
`azurerm_application_insights.main`, **zero creates and zero deletes**. It
changes no role assignments, network exposure, Function resources or alert
thresholds. Plan SHA-256:
`DAFAE90C2D6FFB12F7A91989DE1257ABF1C43E8298ACF37814AE33DD7D6AC86A`.
No apply was performed: this update is outside the prior one-new-alert
preapproval.

Cost check: the workspace's last three days of application telemetry totalled
about 31 MB at the current sampling setting. A conservative fivefold monthly
projection is around 1.6 GB, below the Azure Monitor free ingestion allowance.
The alert rule itself was budgeted at no more than US$0.50/month. After any
approved change, verify two consecutive hourly `AppRequests` and compare
them to `runs` and manifest timestamps before accepting the alert. If Azure
still omits executions, stop and design a separately reviewed independent
manifest freshness probe; do not describe this log-count rule as reliable.

## 3 Nov fallback decision

PR #49 deployed the preferred `host.json` sampling exception for Request and
Exception telemetry, keeping the Application Insights resource at 20%. The
11:00 UTC scheduled housekeeping run published a new manifest, but the
`AppRequests` table still had no row for that execution after 28 minutes.
Therefore the preferred change did not make the existing alert dependable.
The project's 24-hour workspace `Usage` total was about 3.8 MB at 20%; even a
fivefold projection is about 0.57 GB per 30-day month. The earlier 1.6 GB
estimate remains the more conservative budget figure. The 0.1 GB daily cap
remains unchanged. The project manager authorized this fallback if the
preferred host setting failed and log costs remained well within budget.

The replacement saved plan is `tmp/sampling-fallback.tfplan`. Its JSON has one
update to the existing Application Insights component, from 20% to 100%
sampling, with zero creates or deletes; the daily cap, roles and network
settings are unchanged. SHA-256:
`45BF8FB13DC553498636AA6C7FE174C561B31738C3A657F4B20AAE6872819804`.
This change still requires observed hourly request rows and an alert drill
before the monitoring gap can be closed.
