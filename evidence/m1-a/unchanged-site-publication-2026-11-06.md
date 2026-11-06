# Unchanged site publication optimisation

The Azure publisher now hashes the generated event index, per-event summaries,
GeoJSON, outline and processing record. If that digest matches the current
manifest, it does not upload a new generation or replace the manifest. Each
successful hourly timer run writes a small public `data/housekeeping.json`
derived from the run record, including its completion time and build SHA.
Deployment verification reads that heartbeat and Application Insights instead
of assuming that unchanged source data must change `manifest.generated_at`.

After a changed publication commits its manifest, the publisher prunes older
cloud generations and retains the three newest plus the active generation.
The active manifest remains the last write in the publication sequence.

Offline tests cover unchanged skipping, manifest-last writes and pruning. Live
deployment evidence must record the effective SHA, next hourly heartbeat,
manifest behaviour, host managed-identity setting and actual Cost Management
reading. The 6 Nov cost query returned HTTP 429; no charge is inferred.
