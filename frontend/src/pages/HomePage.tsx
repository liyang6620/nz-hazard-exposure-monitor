import { ArrowRight, Database, ShieldCheck, TimerReset } from "lucide-react";
import { Link } from "react-router-dom";

import { ErrorState, LoadingState } from "../components/AsyncState";
import { LatestEventPanel } from "../components/LatestEventPanel";
import { ProcessFlow } from "../components/ProcessFlow";
import { RecentEventsTable } from "../components/RecentEventsTable";
import { useSiteData } from "../app/SiteDataContext";
import { formatNzDateTime } from "../lib/format";

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

  const latest =
    data.events.find(
      (event) => event.event_id === data.manifest.latest_event_id,
    ) ?? data.events[0];
  return (
    <>
      <section className="home-intro">
        <div className="page-container intro-grid">
          <div className="intro-copy">
            <span className="eyebrow">Earthquake exposure intelligence</span>
            <h1>NZ Hazard Exposure Monitor</h1>
            <p className="lede">
              See how many buildings and people are exposed to damaging shaking
              within an hour of a New Zealand earthquake.
            </p>
            <div className="audience-note">
              <ShieldCheck size={19} aria-hidden="true" />
              <span>Built for catastrophe and exposure analysts</span>
            </div>
          </div>
          <div
            className="operational-strip"
            aria-label="Service characteristics"
          >
            <div>
              <TimerReset size={19} />
              <strong>Within one hour</strong>
              <span>Target assessment window</span>
            </div>
            <div>
              <Database size={19} />
              <strong>Evidence linked</strong>
              <span>GeoNet, LINZ and Stats NZ</span>
            </div>
          </div>
        </div>
      </section>
      <div className="page-container home-content">
        {latest ? (
          <LatestEventPanel event={latest} />
        ) : (
          <div className="state-panel">
            No recent earthquakes are available.
          </div>
        )}
        <section className="content-section" aria-labelledby="recent-heading">
          <div className="section-heading">
            <div>
              <span className="eyebrow">Monitored events</span>
              <h2 id="recent-heading">Recent earthquakes</h2>
            </div>
            <span className="updated">
              Data generated {formatNzDateTime(data.manifest.generated_at)}
            </span>
          </div>
          {data.events.length ? (
            <RecentEventsTable events={data.events.slice(0, 8)} />
          ) : (
            <div className="state-panel">
              No M4.0+ earthquakes were returned by GeoNet.
            </div>
          )}
        </section>
        <section
          className="content-section how-it-works"
          aria-labelledby="process-heading"
        >
          <div className="section-heading">
            <div>
              <span className="eyebrow">From event to decision</span>
              <h2 id="process-heading">How it works</h2>
            </div>
          </div>
          <ProcessFlow />
        </section>
        {latest ? (
          <aside className="analysis-cta">
            <div>
              <span className="eyebrow">Latest assessment</span>
              <h2>Inspect the exposure footprint</h2>
              <p>
                Review intensity cells, exposure bands, regional totals and the
                analyst-approved briefing.
              </p>
            </div>
            <Link className="button light" to={`/events/${latest.event_id}`}>
              Open event detail <ArrowRight size={17} />
            </Link>
          </aside>
        ) : null}
      </div>
    </>
  );
}
