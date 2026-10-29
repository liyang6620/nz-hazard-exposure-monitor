import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { EventListItem } from "../data/types";
import { EarthquakeTicker } from "./EarthquakeTicker";

const event: EventListItem = {
  event_id: "recent-event",
  name: "20 km east of Tauranga",
  origin_time: "2026-10-27T03:59:50Z",
  magnitude: 4.2,
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
  as_if_today: true,
  is_recent_monitoring: true,
  is_historical_replay: false,
  map_summary: "Exposure assessment pending.",
  briefing: { status: "pending", title: null, public_path: null },
};

describe("EarthquakeTicker", () => {
  it("reports current monitoring fields without presenting a replay", () => {
    render(<EarthquakeTicker events={[event]} />);
    expect(screen.getAllByText("M4.2").length).toBeGreaterThan(0);
    expect(screen.getAllByText("MMI pending").length).toBeGreaterThan(0);
    expect(screen.queryByText(/historical replay/i)).not.toBeInTheDocument();
  });
});
