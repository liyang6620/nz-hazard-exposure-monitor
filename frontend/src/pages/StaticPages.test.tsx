import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import AboutPage from "./AboutPage";
import MethodologyPage from "./MethodologyPage";
import WorkbenchPage from "./WorkbenchPage";

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

  it("records both operational deployments", () => {
    render(<AboutPage />);
    expect(screen.getByText("Local · operational")).toBeVisible();
    expect(screen.getByText("Azure · operational")).toBeVisible();
    expect(
      screen.getByRole("link", { name: /Analyst Workbench PDF/i }),
    ).toHaveAttribute(
      "href",
      expect.stringContaining("nzhem-powerbi-report.pdf"),
    );
  });

  it("shows the reviewed analyst report snapshot", () => {
    render(
      <MemoryRouter>
        <WorkbenchPage />
      </MemoryRouter>,
    );
    expect(
      screen.getByRole("heading", { name: "Analyst Workbench" }),
    ).toBeVisible();
    expect(
      screen.getByRole("link", { name: /Download five-page PDF/i }),
    ).toHaveAttribute("href", "/workbench/nzhem-powerbi-report.pdf");
    expect(screen.getAllByRole("img", { name: /report canvas/i })).toHaveLength(
      4,
    );
  });
});
