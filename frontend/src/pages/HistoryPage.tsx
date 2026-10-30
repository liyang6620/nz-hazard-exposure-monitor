import { ArrowUpRight } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { useSiteData } from "../app/SiteDataContext";
import { ErrorState, LoadingState } from "../components/AsyncState";
import { HistoryComparisonChart } from "../components/HistoryComparisonChart";
import { loadReplaySummary } from "../data/client";
import { FIXED_REPLAY_IDS } from "../data/history";
import type { EventSummary } from "../data/types";
import {
  displayEventName,
  formatDecimal,
  formatInteger,
  formatNzDateTime,
} from "../lib/format";

export default function HistoryPage() {
  const {
    data,
    error: siteError,
    loading: siteLoading,
    reload,
  } = useSiteData();
  const [events, setEvents] = useState<EventSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!data) return;
    const controller = new AbortController();
    Promise.all(
      FIXED_REPLAY_IDS.map((eventId) =>
        loadReplaySummary(data.manifest.base_path, eventId, controller.signal),
      ),
    )
      .then(setEvents)
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === "AbortError")
          return;
        setError(
          reason instanceof Error
            ? reason.message
            : "Replay data is unavailable",
        );
      });
    return () => controller.abort();
  }, [data]);

  if (siteLoading || (data && !events && !error)) {
    return (
      <div className="page-container">
        <LoadingState label="Loading historical replays" />
      </div>
    );
  }
  if (siteError || error || !data || !events) {
    return (
      <div className="page-container">
        <ErrorState
          message={siteError ?? error ?? "Replay data is unavailable"}
          retry={reload}
        />
      </div>
    );
  }

  return (
    <div className="history-page page-container editorial-page">
      <header className="page-lead">
        <p className="replay-label">Historical replay · as-if-today</p>
        <h1>Ten earthquakes, one current exposure baseline</h1>
        <p>
          These fixed replays apply today’s 3,219,311 mapped buildings and 2023
          population to past shaking. They compare the same exposure baseline,
          not the building stock or population that existed on each event date.
        </p>
      </header>

      <HistoryComparisonChart events={events} />

      <section className="replay-catalogue" aria-labelledby="catalogue-heading">
        <div className="section-heading">
          <h2 id="catalogue-heading">Replay records</h2>
          <span className="updated">10 fixed evaluation events</span>
        </div>
        <div className="replay-list">
          {events.map((event) => (
            <article className="replay-record" key={event.event_id}>
              <div className="replay-record-main">
                <p className="mono">{formatNzDateTime(event.origin_time)}</p>
                <h3>
                  M{formatDecimal(event.magnitude)}{" "}
                  {displayEventName(event.name)}
                </h3>
                <p>
                  {event.no_damaging_shaking
                    ? `No damaging shaking · maximum MMI ${formatDecimal(event.max_mmi)}`
                    : `${formatInteger(event.buildings_mmi_ge_6)} buildings and ${formatInteger(event.population_mmi_ge_6)} people at MMI 6+`}
                </p>
              </div>
              <dl>
                <div>
                  <dt>Maximum MMI</dt>
                  <dd>{formatDecimal(event.max_mmi)}</dd>
                </div>
                <div>
                  <dt>Most affected</dt>
                  <dd>{event.most_affected_region ?? "No MMI 6+ region"}</dd>
                </div>
              </dl>
              <Link
                className="record-link"
                to={`/events/${event.event_id}?view=replay`}
                aria-label={`Open ${displayEventName(event.name)} replay`}
              >
                <ArrowUpRight aria-hidden="true" />
              </Link>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
