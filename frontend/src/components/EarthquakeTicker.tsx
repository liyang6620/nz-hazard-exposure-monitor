import type { EventListItem } from "../data/types";
import { formatDecimal, formatInteger } from "../lib/format";

export function EarthquakeTicker({ events }: { events: EventListItem[] }) {
  if (!events.length) return null;
  const repeated =
    events.length < 4 ? Array(4).fill(events).flat() : [...events, ...events];
  return (
    <div
      className="earthquake-ticker"
      aria-label="Recent GeoNet earthquake updates"
    >
      <div className="ticker-track">
        {repeated.map((event, index) => (
          <span className="ticker-event" key={`${event.event_id}-${index}`}>
            <strong>M{formatDecimal(event.magnitude)}</strong>
            <span>{event.name}</span>
            <span>
              {event.max_mmi === null
                ? "MMI pending"
                : `MMI ${formatDecimal(event.max_mmi)}`}
            </span>
            <span>
              {event.assessment_status === "ready"
                ? `${formatInteger(event.buildings_mmi_ge_6)} buildings at MMI 6+`
                : "Exposure processing"}
            </span>
          </span>
        ))}
      </div>
    </div>
  );
}
