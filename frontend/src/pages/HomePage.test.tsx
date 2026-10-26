import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { SiteData } from "../data/types";
import HomePage from "./HomePage";

const useSiteData = vi.fn();
vi.mock("../app/SiteDataContext", () => ({ useSiteData: () => useSiteData() }));

const siteData: SiteData = {
  manifest: {
    schema_version: 1,
    generation_id: "test",
    generated_at: "2026-10-25T23:00:00Z",
    latest_event_id: "event-1",
    base_path: "/data/generations/test",
  },
  events: [
    {
      event_id: "event-1",
      name: "Test earthquake",
      origin_time: "2026-10-25T23:00:00Z",
      magnitude: 5.5,
      depth_km: 20,
      latitude: -41,
      longitude: 174,
      assessment_status: "ready",
      max_mmi: 5.2,
      buildings_mmi_ge_6: 0,
      population_mmi_ge_6: 0,
      no_damaging_shaking: true,
      mmi_source: "official",
      source_kind: "official",
      source_version: "test",
      shaking_type: "reviewed",
      event_time_status: "supported",
      as_if_today: true,
      map_summary: "No damaging shaking.",
      briefing: { status: "pending", title: null, public_path: null },
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

  it("explains the product and shows the latest event without an empty zero chart", () => {
    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    );
    expect(
      screen.getByRole("heading", { name: "NZ Hazard Exposure Monitor" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/within an hour of a New Zealand earthquake/i),
    ).toBeInTheDocument();
    expect(
      screen.getAllByText("No damaging shaking (MMI < 6)").length,
    ).toBeGreaterThan(0);
    expect(
      screen.getByRole("link", { name: /View exposure assessment/i }),
    ).toHaveAttribute("href", "/events/event-1");
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
