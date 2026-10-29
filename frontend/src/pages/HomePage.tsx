import { Link } from "react-router-dom";

import { ErrorState, LoadingState } from "../components/AsyncState";
import { LatestEventPanel } from "../components/LatestEventPanel";
import { EventWaveform } from "../components/EventWaveform";
import { RecentEventsTable } from "../components/RecentEventsTable";
import { useSiteData } from "../app/SiteDataContext";
import {
  displayEventName,
  formatDecimal,
  formatInteger,
  formatNzDateTime,
  formatElapsed,
} from "../lib/format";

export default function HomePage() {
  const { data, error, loading, reload } = useSiteData();
  if (loading)
    return (
      <div className="page-container">
        <LoadingState />
      </div>
    );
  if (error || !data)
    return (
      <div className="page-container">
        <ErrorState
          message={error ?? "No site data was published"}
          retry={reload}
        />
      </div>
    );

  const latest = data.events.find(
    (event) => event.event_id === data.manifest.latest_event_id,
  );
  const featured =
    data.events.find(
      (event) => event.event_id === data.manifest.featured_event_id,
    ) ?? data.events.find((event) => !event.no_damaging_shaking);
  const recentEvents = data.events.filter(
    (event) => event.is_recent_monitoring,
  );
  return (
    <>
      <section className="home-hero">
        <div className="page-container home-hero-grid">
          {featured ? (
            <div className="featured-replay">
              <p className="replay-label">Historical replay · as-if-today</p>
              <h1>
                M{formatDecimal(featured.magnitude)}{" "}
                {displayEventName(featured.name).replace(/\s+2016$/, "")} —{" "}
                <span>
                  {formatInteger(featured.buildings_mmi_ge_6)} buildings
                </span>{" "}
                in damaging shaking
              </h1>
              <p className="hero-summary">
                A one-hour target view of how many buildings and people are
                exposed to damaging shaking after a New Zealand earthquake. This
                replay uses today’s building stock and 2023 population.
              </p>
              <EventWaveform />
            </div>
          ) : (
            <div className="featured-replay">
              <h1>NZ Hazard Exposure Monitor</h1>
              <p className="hero-summary">
                Buildings and people exposed to damaging New Zealand earthquake
                shaking.
              </p>
            </div>
          )}
          {latest ? (
            <LatestEventPanel event={latest} />
          ) : (
            <aside className="latest-event state-panel">
              No GeoNet M4.0+ events were recorded in the past 30 days.
            </aside>
          )}
        </div>
      </section>
      {featured ? (
        <div
          className="page-container replay-metrics"
          aria-label="Featured replay summary"
        >
          <div>
            <strong>{formatInteger(featured.population_mmi_ge_6)}</strong>
            <span>people at MMI 6+</span>
          </div>
          <div>
            <strong>{formatDecimal(featured.max_mmi)}</strong>
            <span>maximum populated MMI</span>
          </div>
          <div>
            <strong>
              {featured.most_affected_region ?? "Marlborough Region"}
            </strong>
            <span>most affected region</span>
          </div>
        </div>
      ) : null}
      <div className="page-container home-content">
        {data.manifest.processing_record ? (
          <section
            className="processing-record"
            aria-labelledby="processing-record-heading"
          >
            <div>
              <h2 id="processing-record-heading">Observed processing time</h2>
              <p>
                A real GeoNet event processed by the continuously running local
                monitor.
              </p>
            </div>
            <dl>
              <div>
                <dt>Earthquake</dt>
                <dd>
                  {formatNzDateTime(
                    data.manifest.processing_record.earthquake_at,
                  )}
                </dd>
              </div>
              <div>
                <dt>Site published</dt>
                <dd>
                  {formatNzDateTime(
                    data.manifest.processing_record.published_at,
                  )}
                </dd>
              </div>
              <div>
                <dt>Total elapsed</dt>
                <dd>
                  {formatElapsed(
                    data.manifest.processing_record.elapsed_seconds,
                  )}
                </dd>
              </div>
            </dl>
          </section>
        ) : null}
        <section className="content-section" aria-labelledby="recent-heading">
          <div className="section-heading">
            <h2 id="recent-heading">Latest monitored events</h2>
            <span className="updated">
              Data generated {formatNzDateTime(data.manifest.generated_at)}
            </span>
          </div>
          {recentEvents.length ? (
            <RecentEventsTable events={recentEvents.slice(0, 8)} />
          ) : (
            <div className="state-panel">
              No GeoNet M4.0+ events were recorded in the past 30 days.
            </div>
          )}
        </section>
        {featured ? (
          <p className="history-link">
            Compare Kaikōura with nine other fixed events in the{" "}
            <Link to="/history">historical replay catalogue</Link>, or open the{" "}
            <Link to={`/events/${featured.event_id}`}>
              full Kaikōura record
            </Link>
            .
          </p>
        ) : null}
      </div>
    </>
  );
}
