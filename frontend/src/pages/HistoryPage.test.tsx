import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { EventSummary, SiteData } from "../data/types";
import { FIXED_REPLAY_IDS } from "../data/history";
import HistoryPage from "./HistoryPage";

const useSiteData = vi.fn();
const loadEventSummary = vi.fn();

vi.mock("../app/SiteDataContext", () => ({ useSiteData: () => useSiteData() }));
vi.mock("../data/client", () => ({
  loadEventSummary: (...args: unknown[]) => loadEventSummary(...args),
}));
vi.mock("../components/HistoryComparisonChart", () => ({
  HistoryComparisonChart: ({ events }: { events: EventSummary[] }) => (
    <div data-testid="comparison">{events.length} events compared</div>
  ),
}));

const siteData: SiteData = {
  manifest: {
    schema_version: 1,
    generation_id: "test",
    generated_at: "2026-10-29T00:20:49Z",
    latest_event_id: null,
    featured_event_id: "2016p858000",
    base_path: "/data/generations/test",
  },
  events: [],
};

function summary(eventId: string): EventSummary {
  const isChristchurch = eventId === "3468575";
  return {
    event_id: eventId,
    name: isChristchurch ? "Christchurch Feb 2011" : `Replay ${eventId}`,
    origin_time: "2011-02-22T12:51:42+13:00",
    magnitude: 6.2,
    depth_km: 5.4,
    latitude: -43.582,
    longitude: 172.678,
    assessment_status: "ready",
    max_mmi: 9.4,
    buildings_mmi_ge_6: 270518,
    population_mmi_ge_6: 461765,
    no_damaging_shaking: false,
    mmi_source: "official",
    source_kind: "official",
    source_version: "reviewed",
    shaking_type: "reviewed",
    event_time_status: "not_supported",
    as_if_today: true,
    is_recent_monitoring: false,
    is_historical_replay: true,
    most_affected_region: "Canterbury Region",
    map_summary: "Canterbury Region was most affected.",
    briefing: {
      status: "approved",
      title: "Approved",
      public_path: "/briefing",
    },
    mmi_bands: [],
    regions: [],
  };
}

describe("HistoryPage", () => {
  beforeEach(() => {
    useSiteData.mockReturnValue({
      data: siteData,
      error: null,
      loading: false,
      reload: vi.fn(),
    });
    loadEventSummary.mockImplementation((_basePath: string, eventId: string) =>
      Promise.resolve(summary(eventId)),
    );
  });

  it("loads the ten fixed summaries and presents natural event names", async () => {
    render(
      <MemoryRouter>
        <HistoryPage />
      </MemoryRouter>,
    );

    await waitFor(() =>
      expect(screen.getByTestId("comparison")).toHaveTextContent("10 events"),
    );
    expect(loadEventSummary).toHaveBeenCalledTimes(FIXED_REPLAY_IDS.length);
    expect(screen.getByText(/Christchurch, Feb 2011/)).toBeInTheDocument();
    expect(screen.getAllByRole("article")).toHaveLength(10);
    expect(
      screen.getByText(/today’s 3,219,311 mapped buildings/i),
    ).toBeInTheDocument();
  });
});
