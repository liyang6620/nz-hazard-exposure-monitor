import { ArrowUpRight } from "lucide-react";
import { Link } from "react-router-dom";

import type { EventListItem } from "../data/types";
import { formatDecimal, formatInteger, formatNzDateTime } from "../lib/format";
import { StatusBadge } from "./StatusBadge";

export function RecentEventsTable({ events }: { events: EventListItem[] }) {
  return (
    <div className="table-wrap">
      <table>
        <caption className="sr-only">
          Recent earthquakes and exposure results
        </caption>
        <thead>
          <tr>
            <th>Earthquake</th>
            <th>Time</th>
            <th>Magnitude</th>
            <th>Maximum MMI</th>
            <th>Buildings at MMI 6+</th>
            <th>Status</th>
            <th>
              <span className="sr-only">Open</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {events.map((event, index) => (
            <tr
              className={index === 0 ? "latest-row" : undefined}
              key={event.event_id}
            >
              <th scope="row">
                {index === 0 ? (
                  <span className="latest-marker">Latest</span>
                ) : null}
                <Link to={`/events/${event.event_id}`}>{event.name}</Link>
              </th>
              <td>{formatNzDateTime(event.origin_time)}</td>
              <td>{formatDecimal(event.magnitude)}</td>
              <td>
                {event.assessment_status === "ready"
                  ? formatDecimal(event.max_mmi)
                  : "Pending"}
              </td>
              <td>{formatInteger(event.buildings_mmi_ge_6)}</td>
              <td>
                <StatusBadge event={event} />
              </td>
              <td>
                <Link
                  className="row-link"
                  to={`/events/${event.event_id}`}
                  aria-label={`View ${event.name}`}
                >
                  <ArrowUpRight size={17} />
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
