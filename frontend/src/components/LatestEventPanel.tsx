import { ArrowRight, Building2, Clock3, Gauge, Users } from "lucide-react";
import { Link } from "react-router-dom";

import type { EventListItem } from "../data/types";
import {
  formatDecimal,
  formatInteger,
  formatNzDateTime,
  statusMessage,
} from "../lib/format";
import { MetricCard } from "./MetricCard";
import { StatusBadge } from "./StatusBadge";

export function LatestEventPanel({ event }: { event: EventListItem }) {
  const status = statusMessage(event);
  return (
    <section className="latest-event" aria-labelledby="latest-heading">
      <div className="latest-heading-row">
        <div>
          <span className="eyebrow">Latest monitored earthquake</span>
          <h2 id="latest-heading">{event.name}</h2>
          <p className="event-time">
            <Clock3 size={16} aria-hidden="true" />
            {formatNzDateTime(event.origin_time)}
          </p>
        </div>
        <StatusBadge event={event} />
      </div>
      <div className="metric-grid">
        <MetricCard
          label="Magnitude"
          value={formatDecimal(event.magnitude)}
          detail={`${formatDecimal(event.depth_km)} km deep`}
          icon={<Gauge size={17} />}
        />
        <MetricCard
          label="Maximum MMI"
          value={formatDecimal(event.max_mmi)}
          detail={
            event.source_kind === "official"
              ? "Official shaking layer"
              : "Preliminary estimate"
          }
          icon={<ActivityIcon />}
        />
        <MetricCard
          label="Buildings at MMI 6+"
          value={formatInteger(event.buildings_mmi_ge_6)}
          icon={<Building2 size={17} />}
        />
        <MetricCard
          label="People at MMI 6+"
          value={formatInteger(event.population_mmi_ge_6)}
          icon={<Users size={17} />}
        />
      </div>
      {status ? <p className="event-callout">{status}</p> : null}
      <Link className="button primary" to={`/events/${event.event_id}`}>
        View exposure assessment <ArrowRight size={17} />
      </Link>
    </section>
  );
}

function ActivityIcon() {
  return (
    <span className="mmi-icon" aria-hidden="true">
      VI
    </span>
  );
}
