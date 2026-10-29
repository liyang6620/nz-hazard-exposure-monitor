import { ArrowLeft, Info, MapPin } from "lucide-react";
import { lazy, Suspense, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { useSiteData } from "../app/SiteDataContext";
import { ErrorState, LoadingState } from "../components/AsyncState";
import { ExposureCharts } from "../components/ExposureCharts";
import { MetricCard } from "../components/MetricCard";
import { RegionExposureTable } from "../components/RegionExposureTable";
import { StatusBadge } from "../components/StatusBadge";
import { eventExposureUrl, loadEventSummary } from "../data/client";
import type { EventSummary } from "../data/types";
import {
  displayEventName,
  formatDecimal,
  formatInteger,
  formatNzDateTime,
  formatSourceVersion,
  statusMessage,
} from "../lib/format";

const EventMap = lazy(() => import("../map/EventMap"));

export default function EventDetailPage() {
  const { eventId = "" } = useParams();
  const { data, error: siteError, loading: siteLoading } = useSiteData();
  const [state, setState] = useState<{
    eventId: string;
    event: EventSummary | null;
    error: string | null;
  }>({ eventId: "", event: null, error: null });

  useEffect(() => {
    if (!data || !eventId) return;
    const controller = new AbortController();
    loadEventSummary(data.manifest.base_path, eventId, controller.signal)
      .then((event) => setState({ eventId, event, error: null }))
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === "AbortError")
          return;
        setState({
          eventId,
          event: null,
          error:
            reason instanceof Error
              ? reason.message
              : "Event data is unavailable",
        });
      });
    return () => controller.abort();
  }, [data, eventId]);

  const event = state.eventId === eventId ? state.event : null;
  const error = state.eventId === eventId ? state.error : null;

  if (siteLoading || (data && !event && !error))
    return (
      <div className="page-container">
        <LoadingState label="Loading earthquake assessment" />
      </div>
    );
  if (siteError || error || !data || !event)
    return (
      <div className="page-container">
        <ErrorState message={siteError ?? error ?? "Earthquake not found"} />
      </div>
    );

  const status = statusMessage(event);
  return (
    <div className="event-page">
      <section className="event-header">
        <div className="page-container">
          <Link className="back-link" to="/">
            <ArrowLeft size={17} />
            Back to overview
          </Link>
          <div className="event-title-row">
            <div>
              {event.is_historical_replay ? (
                <p className="replay-label">Historical replay · as-if-today</p>
              ) : null}
              <div className="event-name-line">
                <h1>{displayEventName(event.name)}</h1>
                {event.as_if_today ? (
                  <span className="as-if-note">As-if-today</span>
                ) : null}
              </div>
              <p>
                <MapPin size={16} />
                {event.latitude.toFixed(3)}, {event.longitude.toFixed(3)} ·{" "}
                {formatNzDateTime(event.origin_time)}
              </p>
              {event.as_if_today ? (
                <p className="as-if-explanation">
                  Exposure is recalculated using today’s building stock and 2023
                  population, not the assets present on the event date.
                </p>
              ) : null}
            </div>
            <StatusBadge event={event} />
          </div>
          <div className="metric-grid event-metrics">
            <MetricCard
              label="Magnitude"
              value={formatDecimal(event.magnitude)}
              detail={`${formatDecimal(event.depth_km)} km deep`}
            />
            <MetricCard
              label="Maximum MMI"
              value={formatDecimal(event.max_mmi)}
              detail="Highest populated intensity"
            />
            <MetricCard
              label="Buildings at MMI 6+"
              value={formatInteger(event.buildings_mmi_ge_6)}
            />
            <MetricCard
              label="People at MMI 6+"
              value={formatInteger(event.population_mmi_ge_6)}
            />
          </div>
          {status ? <p className="event-callout">{status}</p> : null}
        </div>
      </section>
      <div className="page-container event-content">
        <section className="map-section" aria-labelledby="map-heading">
          <div className="section-heading">
            <h2 id="map-heading">Shaking and exposure map</h2>
            <span className={`source-chip ${event.source_kind}`}>
              {event.source_kind === "official"
                ? "Official shaking layer"
                : "Preliminary estimate"}
            </span>
          </div>
          <div className="map-layout">
            <Suspense
              fallback={<LoadingState label="Loading interactive map" />}
            >
              <EventMap
                event={event}
                exposureUrl={eventExposureUrl(
                  data.manifest.base_path,
                  event.event_id,
                )}
              />
            </Suspense>
            <aside
              className="map-alternative"
              aria-label="Text alternative to the exposure map"
            >
              <Info size={20} aria-hidden="true" />
              <div>
                <strong>Map summary</strong>
                <p>{event.map_summary}</p>
                <div className="mmi-legend" aria-label="MMI colour legend">
                  <span>
                    <i className="epicentre-symbol" />
                    Epicentre
                  </span>
                  <span>
                    <i className="mmi5" />
                    MMI 5
                  </span>
                  <span>
                    <i className="mmi6" />
                    MMI 6
                  </span>
                  <span>
                    <i className="mmi7" />
                    MMI 7
                  </span>
                  <span>
                    <i className="mmi8" />
                    MMI 8+
                  </span>
                </div>
              </div>
            </aside>
          </div>
        </section>
        {!event.no_damaging_shaking && event.assessment_status === "ready" ? (
          <>
            <section
              className="content-section"
              aria-labelledby="bands-heading"
            >
              <div className="section-heading">
                <h2 id="bands-heading">Exposure by MMI band</h2>
              </div>
              <ExposureCharts bands={event.mmi_bands} />
            </section>
            <section
              className="content-section"
              aria-labelledby="regions-heading"
            >
              <div className="section-heading">
                <h2 id="regions-heading">Regional exposure at MMI 6+</h2>
              </div>
              <RegionExposureTable regions={event.regions} />
            </section>
          </>
        ) : null}
        <section
          className="content-section briefing-section"
          aria-labelledby="briefing-heading"
        >
          <div>
            <h2 id="briefing-heading">Approved event briefing</h2>
          </div>
          {event.briefing.status === "approved" &&
          event.briefing.public_path ? (
            <iframe
              title="Approved event briefing"
              src={event.briefing.public_path}
            />
          ) : (
            <div className="pending-briefing">
              <Info size={20} />
              <div>
                <strong>Pending approval</strong>
                <p>
                  The draft is not public until an analyst verifies and approves
                  it.
                </p>
              </div>
            </div>
          )}
        </section>
        <section className="data-note" aria-label="Data provenance">
          <strong>Data and interpretation</strong>
          <p>
            Earthquake and shaking data: GeoNet / Earth Sciences New Zealand.
            Buildings: Toitū Te Whenua LINZ. Population: 2023 Census, Stats NZ.
            Exposure uses today’s building stock and 2023 population.
          </p>
          <dl>
            <div>
              <dt>Shaking version</dt>
              <dd title={event.source_version ?? undefined}>
                {formatSourceVersion(event.source_version, event.shaking_type)}
              </dd>
            </div>
            <div>
              <dt>Assessment basis</dt>
              <dd>{event.as_if_today ? "As-if-today" : "Event time"}</dd>
            </div>
          </dl>
        </section>
      </div>
    </div>
  );
}
