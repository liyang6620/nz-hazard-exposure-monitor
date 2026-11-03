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
