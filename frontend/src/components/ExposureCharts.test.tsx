import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { chartBands } from "../lib/mmi";
import { ExposureCharts } from "./ExposureCharts";

describe("ExposureCharts", () => {
  it("summarises low intensity exposure and keeps MMI 5+ as chart data", () => {
    render(
      <ExposureCharts
        bands={[
          { mmi_band: "<4", buildings: 2000000, population: 3000000 },
          { mmi_band: "4", buildings: 200000, population: 300000 },
          { mmi_band: "5", buildings: 10000, population: 20000 },
          { mmi_band: "6", buildings: 1000, population: 2000 },
          { mmi_band: "7", buildings: 100, population: 200 },
          { mmi_band: "8+", buildings: 10, population: 20 },
        ]}
      />,
    );

    expect(
      screen.getByText(/2,200,000 buildings and 3,300,000 people/),
    ).toBeInTheDocument();
    expect(
      chartBands([
        { mmi_band: "<4", buildings: 1, population: 1 },
        { mmi_band: "4", buildings: 1, population: 1 },
        { mmi_band: "5", buildings: 1, population: 1 },
        { mmi_band: "6", buildings: 1, population: 1 },
        { mmi_band: "7", buildings: 1, population: 1 },
        { mmi_band: "8+", buildings: 1, population: 1 },
      ]).map((band) => band.mmi_band),
    ).toEqual(["5", "6", "7", "8+"]);
  });
});
