import type { EventListItem } from "../data/types";

export function StatusBadge({ event }: { event: EventListItem }) {
  if (event.assessment_status !== "ready")
    return <span className="badge pending">Assessment pending</span>;
  if (event.no_damaging_shaking)
    return <span className="badge quiet">MMI below 6</span>;
  return <span className="badge damaging">Damaging shaking</span>;
}
