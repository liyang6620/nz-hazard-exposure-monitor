import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import type { EventSummary, SiteData } from "../data/types";
import EventDetailPage from "./EventDetailPage";

const useSiteData = vi.fn();
const loadEventSummary = vi.fn();
const loadReplaySummary = vi.fn();

vi.mock("../app/SiteDataContext", () => ({ useSiteData: () => useSiteData() }));
vi.mock("../data/client", () => ({
  loadEventSummary: (...args: unknown[]) => loadEventSummary(...args),
  loadReplaySummary: (...args: unknown[]) => loadReplaySummary(...args),
  eventExposureUrl: () => "/event.geojson",
  replayExposureUrl: () => "/replay.geojson",
}));
vi.mock("../map/EventMap", () => ({
  default: ({ exposureUrl }: { exposureUrl: string }) => (
    <div data-testid="event-map">{exposureUrl}</div>
  ),
}));

const event: EventSummary = {
  event_id: "2026p776286",
  name: "30 km north-east of Taumarunui",
  origin_time: "2026-10-15T05:25:34Z",
  magnitude: 5.7,
  magnitude_type: "M",
  magnitude_revision_time: "2026-10-15T05:53:42Z",
  depth_km: 268.7,
  latitude: -38.623,
  longitude: 175.452,
  assessment_status: "ready",
  max_mmi: 2.8,
  buildings_mmi_ge_6: 0,
  population_mmi_ge_6: 0,
  no_damaging_shaking: true,
  mmi_source: "official",
  source_kind: "official",
  source_version: "2026-10-16T05:27:46-auto",
  shaking_type: "auto",
  event_time_status: "supported",
  as_if_today: true,
  is_recent_monitoring: false,
  is_historical_replay: true,
  most_affected_region: null,
  map_summary: "No damaging shaking (MMI < 6).",
  briefing: { status: "pending", title: null, public_path: null },
  mmi_bands: [],
  regions: [],
};

const siteData: SiteData = {
  manifest: {
    schema_version: 1,
    generation_id: "test",
    generated_at: "2026-10-30T00:00:00Z",
    latest_event_id: event.event_id,
    featured_event_id: event.event_id,
    base_path: "/data/generations/test",
  },
  events: [],
};

describe("EventDetailPage", () => {
  it("loads the replay view and shows GeoNet magnitude revision metadata", async () => {
    useSiteData.mockReturnValue({
      data: siteData,
      error: null,
      loading: false,
    });
    loadReplaySummary.mockResolvedValue(event);

    render(
      <MemoryRouter initialEntries={["/events/2026p776286?view=replay"]}>
        <Routes>
          <Route path="/events/:eventId" element={<EventDetailPage />} />
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() => expect(loadReplaySummary).toHaveBeenCalledOnce());
    expect(loadEventSummary).not.toHaveBeenCalled();
    expect(screen.getByText("Historical replay · as-if-today")).toBeVisible();
    expect(
      screen.getByText("M · revised 15 Oct 2026, 18:53 NZDT"),
    ).toBeVisible();
    expect(await screen.findByTestId("event-map")).toHaveTextContent(
      "/replay.geojson",
    );
  });
});
