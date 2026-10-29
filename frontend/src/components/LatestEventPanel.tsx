import { ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";

import type { EventListItem } from "../data/types";
import {
  displayEventName,
  formatDecimal,
  formatInteger,
  formatNzDateTime,
  statusMessage,
} from "../lib/format";

export function LatestEventPanel({ event }: { event: EventListItem }) {
  const status = statusMessage(event);
  return (
    <aside className="latest-event" aria-labelledby="latest-heading">
      <div className="latest-panel-heading">
        <span>Latest event</span>
        <time>{formatNzDateTime(event.origin_time)}</time>
      </div>
      <p className="latest-magnitude">M{formatDecimal(event.magnitude)}</p>
      <h2 id="latest-heading">{displayEventName(event.name)}</h2>
      <p className="latest-depth">{formatDecimal(event.depth_km)} km depth</p>
      <dl className="latest-readings">
        <div>
          <dt>Maximum MMI</dt>
          <dd>{formatDecimal(event.max_mmi)}</dd>
        </div>
        <div>
          <dt>Buildings at MMI 6+</dt>
          <dd>{formatInteger(event.buildings_mmi_ge_6)}</dd>
        </div>
        <div>
          <dt>People at MMI 6+</dt>
          <dd>{formatInteger(event.population_mmi_ge_6)}</dd>
        </div>
      </dl>
      {status ? (
        <p className="latest-status">{status}</p>
      ) : (
        <p className="latest-status damaging">Damaging shaking recorded</p>
      )}
      <Link className="text-link" to={`/events/${event.event_id}`}>
        View exposure assessment <ArrowRight size={17} />
      </Link>
    </aside>
  );
}
