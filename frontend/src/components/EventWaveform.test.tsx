import { render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { EventWaveform } from "./EventWaveform";

afterEach(() => vi.unstubAllGlobals());

it("shows an error instead of loading forever when the waveform is missing", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false }));

  render(<EventWaveform />);

  expect(
    await screen.findByText("GeoNet waveform unavailable."),
  ).toBeInTheDocument();
});
