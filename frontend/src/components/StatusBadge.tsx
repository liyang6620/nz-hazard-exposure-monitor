import type { EventListItem } from "../data/types";

export function StatusBadge({ event }: { event: EventListItem }) {
  if (event.assessment_status === "outside_model_range")
    return <span className="event-status terminal">Outside model range</span>;
  if (event.assessment_status === "expired")
    return (
      <span className="event-status terminal">Outside monitoring window</span>
    );
  if (event.assessment_status === "timed_out")
    return <span className="event-status terminal">Assessment timed out</span>;
  if (event.assessment_status === "failed")
    return <span className="event-status terminal">Assessment failed</span>;
  if (event.assessment_status !== "ready")
    return <span className="event-status pending">Assessment pending</span>;
  if (event.no_damaging_shaking)
    return <span className="event-status quiet">MMI below 6</span>;
  return <span className="event-status damaging">Damaging shaking</span>;
}
