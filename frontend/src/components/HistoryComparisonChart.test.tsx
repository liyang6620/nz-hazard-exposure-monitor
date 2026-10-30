import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { EventSummary } from "../data/types";
import { HistoryComparisonChart } from "./HistoryComparisonChart";

describe("HistoryComparisonChart", () => {
  it("shows explicit buildings and people legend labels", () => {
    render(
      <HistoryComparisonChart
        events={
          [
            {
              event_id: "event-1",
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
              no_damaging_shaking: false,
              mmi_source: "official",
              source_kind: "official",
              source_version: "reviewed",
              shaking_type: "reviewed",
              event_time_status: "not_supported",
              as_if_today: true,
              map_summary: "Marlborough Region was most affected.",
              most_affected_region: "Marlborough Region",
              mmi_bands: [],
              regions: [],
              briefing: { status: "approved", title: null, public_path: null },
              is_recent_monitoring: false,
              is_historical_replay: true,
            },
          ] as EventSummary[]
        }
      />,
    );

    const legend = screen.getByLabelText("Comparison chart legend");
    expect(legend).toHaveTextContent("Buildings");
    expect(legend).toHaveTextContent("People");
  });
});
