# ADR 0009: Separate as-if-today replays from event-time monitoring

Status: accepted at Checkpoint A; maintained in the public product.

## Context

The LINZ building export's lifecycle begins on 16 Oct 2018. Eight of the ten
fixed earthquakes precede that coverage. Calling current buildings a 2010-16
inventory would create false historical exposure. The approved population
layer is the 2023 Census SA1 release.

## Decision

Apply each fixed historical shaking surface to the 3,219,311 current
deduplicated buildings and allocated 2023 population, labelled
**historical replay, as-if-today**. Do not report unsupported pre-2018
event-time building counts as zero. Real-time monitoring uses building validity
at the event timestamp; its 2023 population basis remains explicit. Keep
live and replay assessments distinct even if they share a GeoNet event ID.

## Consequences

All ten fixed replays use official GeoNet Shaking Layers. Kaikōura's replay
reports 78,564 buildings and 83,276 people at MMI 6+, but these are not
claims about 2016 buildings. The public site, briefings and Analyst Workbench
show the basis. The Power BI comparison page contains only the ten replays;
the all-event chronology deduplicates shared GeoNet IDs.

See [Checkpoint A](../../evidence/checkpoint-a/README.md),
[M3 results](../../evidence/m3/README.md) and
[Workbench method](../powerbi.md).
