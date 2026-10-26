import { describe, expect, it } from "vitest";

import { formatInteger, formatNzDateTime, statusMessage } from "./format";

describe("New Zealand display formatting", () => {
  it("displays dates in Pacific/Auckland with the local time-zone abbreviation", () => {
    expect(formatNzDateTime("2026-10-25T23:00:00Z")).toBe(
      "26 Oct 2026, 12:00 NZDT",
    );
    expect(formatNzDateTime("2026-06-01T00:00:00Z")).toBe(
      "01 Jun 2026, 12:00 NZST",
    );
  });

  it("formats exposure counts and pending values", () => {
    expect(formatInteger(78564)).toBe("78,564");
    expect(formatInteger(null)).toBe("Pending");
  });

  it("uses the required pending and non-damaging wording", () => {
    expect(
      statusMessage({
        assessment_status: "processing",
        no_damaging_shaking: false,
      }),
    ).toBe("Exposure assessment pending");
    expect(
      statusMessage({ assessment_status: "ready", no_damaging_shaking: true }),
    ).toBe("No damaging shaking (MMI < 6)");
  });
});
