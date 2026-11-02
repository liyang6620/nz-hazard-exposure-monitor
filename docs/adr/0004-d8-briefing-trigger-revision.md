# ADR 0004: D8 briefing trigger revision

Status: project-manager approved, 2 November 2026.

Briefings are generated only when the **maximum MMI in populated exposure
cells is at least 5.0**. Earthquake magnitude by itself does not qualify an
event. A remote M5.0 event with populated maximum MMI 0.8, for example, stays
on the website as an assessed event but produces no draft, email or LLM call.

The existing material-revision threshold remains: a new draft for an already
briefed event requires a magnitude revision of at least 0.3. Both local and
Azure entry points apply the populated-MMI gate before any model call. The
per-briefing token and monthly-count ceilings remain in force.

Realtime assessment computes the maximum over cells with allocated population
greater than zero. It also records whether the unrounded maximum crosses 5.0,
so rounding the published MMI to one decimal cannot create a false trigger.
