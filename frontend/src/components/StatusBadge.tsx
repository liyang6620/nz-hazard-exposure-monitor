import type { EventListItem } from "../data/types";

export function StatusBadge({ event }: { event: EventListItem }) {
  if (event.assessment_status !== "ready")
    return <span className="event-status pending">Assessment pending</span>;
  if (event.no_damaging_shaking)
    return <span className="event-status quiet">MMI below 6</span>;
  return <span className="event-status damaging">Damaging shaking</span>;
}
