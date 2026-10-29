import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import AboutPage from "./AboutPage";
import MethodologyPage from "./MethodologyPage";

describe("product information pages", () => {
  it("records the approved method and known limitations", () => {
    render(<MethodologyPage />);
    expect(
      screen.getByRole("heading", { name: "Method and data" }),
    ).toBeVisible();
    expect(screen.getByText(/MAE is 1\.049 MMI/i)).toBeVisible();
    expect(screen.getByText(/21,483 building outlines/i)).toBeVisible();
    expect(screen.getByText(/Chatham Islands/i)).toBeVisible();
  });

  it("distinguishes the operational local target from planned Azure deployment", () => {
    render(<AboutPage />);
    expect(screen.getByText("Local · operational")).toBeVisible();
    expect(screen.getByText("Azure · planned")).toBeVisible();
    expect(
      screen.getByRole("link", { name: /Power BI report/i }),
    ).toHaveAttribute(
      "href",
      expect.stringContaining("nzhem-powerbi-report.pdf"),
    );
  });
});
