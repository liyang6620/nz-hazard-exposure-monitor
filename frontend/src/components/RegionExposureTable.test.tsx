import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { RegionExposureTable } from "./RegionExposureTable";

describe("RegionExposureTable", () => {
  it("omits regions whose building and population totals are both zero", () => {
    render(
      <RegionExposureTable
        regions={[
          {
            region_code: "MBH",
            region_name: "Marlborough Region",
            buildings: 12,
            population: 20,
          },
          {
            region_code: "unknown",
            region_name: "Unknown region",
            buildings: 0,
            population: 0,
          },
        ]}
      />,
    );

    expect(screen.getByText("Marlborough Region")).toBeInTheDocument();
    expect(screen.queryByText("Unknown region")).not.toBeInTheDocument();
  });

  it("renames populated unmapped exposure and explains it", () => {
    render(
      <RegionExposureTable
        regions={[
          {
            region_code: "outside",
            region_name: "Unknown region",
            buildings: 7,
            population: 11,
          },
        ]}
      />,
    );

    expect(screen.getByText("Outside mapped regions")).toBeInTheDocument();
    expect(
      screen.getByText(/has no matching regional boundary/i),
    ).toBeInTheDocument();
  });
});
