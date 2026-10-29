import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { EventListItem, SiteData } from "../data/types";
import HomePage from "./HomePage";

const useSiteData = vi.fn();
vi.mock("../app/SiteDataContext", () => ({ useSiteData: () => useSiteData() }));

const baseEvent: EventListItem = {
  event_id: "recent-event",
  name: "20 km east of Tauranga",
  origin_time: "2026-10-27T03:59:50Z",
  magnitude: 4.2,
  magnitude_type: "M",
  magnitude_revision_time: "2026-10-27T04:05:00Z",
  depth_km: 20,
  latitude: -37.6,
  longitude: 176.4,
  assessment_status: "processing",
  max_mmi: null,
  buildings_mmi_ge_6: null,
  population_mmi_ge_6: null,
  no_damaging_shaking: false,
  mmi_source: null,
  source_kind: "preliminary",
  source_version: null,
  shaking_type: "preliminary",
  event_time_status: "pending",
  as_if_today: false,
  is_recent_monitoring: true,
  is_historical_replay: false,
  most_affected_region: null,
  map_summary: "Exposure assessment pending.",
  briefing: { status: "pending", title: null, public_path: null },
};

const siteData: SiteData = {
  manifest: {
    schema_version: 1,
    generation_id: "test",
    generated_at: "2026-10-28T11:00:00Z",
    latest_event_id: "recent-event",
    featured_event_id: "replay-event",
    base_path: "/data/generations/test",
  },
  events: [
    baseEvent,
    {
      ...baseEvent,
      event_id: "replay-event",
      name: "Kaikōura 2016",
      origin_time: "2016-11-13T11:02:56Z",
      magnitude: 7.8,
      magnitude_type: "Mw",
      magnitude_revision_time: "2016-11-13T12:00:00Z",
      depth_km: 15.1,
      latitude: -42.693,
      longitude: 173.022,
      assessment_status: "ready",
      max_mmi: 8.4,
      buildings_mmi_ge_6: 78564,
      population_mmi_ge_6: 83276,
      mmi_source: "official",
      source_kind: "official",
      source_version: "2025-09-22T21:53:33-reviewed",
      shaking_type: "reviewed",
      event_time_status: "not_supported",
      is_recent_monitoring: false,
      is_historical_replay: true,
      most_affected_region: "Marlborough Region",
      map_summary: "Marlborough Region was most affected.",
    },
    {
      ...baseEvent,
      event_id: "old-event",
      name: "Darfield 2010",
      origin_time: "2010-09-03T16:35:41Z",
      is_recent_monitoring: false,
      is_historical_replay: true,
    },
  ],
};

describe("HomePage", () => {
  beforeEach(() =>
    useSiteData.mockReturnValue({
      data: siteData,
      error: null,
      loading: false,
      reload: vi.fn(),
    }),
  );

  it("separates the featured historical replay from current monitoring", () => {
    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    );
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
      /M7\.8 Kaikōura/i,
    );
    expect(
      screen.getByText("Historical replay · as-if-today"),
    ).toBeInTheDocument();
    expect(screen.getByText("Latest event")).toBeInTheDocument();
    expect(
      screen.getAllByText("20 km east of Tauranga").length,
    ).toBeGreaterThan(0);
    expect(screen.getByText("Latest")).toBeInTheDocument();
    expect(screen.queryByText("Darfield 2010")).not.toBeInTheDocument();
    expect(screen.queryByText(/No numbered steps/i)).not.toBeInTheDocument();
    expect(screen.getByText(/one-hour target view/i)).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "Observed processing time" }),
    ).not.toBeInTheDocument();
  });

  it("shows processing time only when the publisher supplies a real record", () => {
    useSiteData.mockReturnValue({
      data: {
        ...siteData,
        manifest: {
          ...siteData.manifest,
          processing_record: {
            event_id: "recent-event",
            earthquake_at: "2026-10-29T00:00:00Z",
            published_at: "2026-10-29T00:18:00Z",
            elapsed_seconds: 1080,
          },
        },
      },
      error: null,
      loading: false,
      reload: vi.fn(),
    });
    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    );
    expect(
      screen.getByRole("heading", { name: "Observed processing time" }),
    ).toBeInTheDocument();
    expect(screen.getByText("18m 0s")).toBeInTheDocument();
  });

  it("renders a retryable error state", () => {
    useSiteData.mockReturnValue({
      data: null,
      error: "Unavailable",
      loading: false,
      reload: vi.fn(),
    });
    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Unavailable");
  });
});
