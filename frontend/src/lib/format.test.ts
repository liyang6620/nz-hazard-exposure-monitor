import { describe, expect, it } from "vitest";

import {
  displayEventName,
  formatDecimal,
  formatInteger,
  formatNzDateTime,
  formatSourceVersion,
  statusMessage,
} from "./format";

describe("New Zealand display formatting", () => {
  it("uses natural display names without changing data identifiers", () => {
    expect(displayEventName("Christchurch Feb 2011")).toBe(
      "Christchurch, Feb 2011",
    );
    expect(displayEventName("Kaikōura 2016")).toBe("Kaikōura 2016");
  });
  it("displays dates in Pacific/Auckland with the local time-zone abbreviation", () => {
    expect(formatNzDateTime("2026-10-25T23:00:00Z")).toBe(
      "26 Oct 2026, 12:00 NZDT",
    );
    expect(formatNzDateTime("2026-06-01T00:00:00Z")).toBe(
      "1 Jun 2026, 12:00 NZST",
    );
  });

  it("formats exposure counts and pending values", () => {
    expect(formatInteger(78564)).toBe("78,564");
    expect(formatInteger(null)).toBe("Pending");
    expect(formatDecimal(6)).toBe("6.0");
    expect(formatDecimal(8.04)).toBe("8.0");
  });

  it("turns shaking versions into a readable label", () => {
    expect(
      formatSourceVersion("2025-09-22T21:53:33-reviewed", "reviewed"),
    ).toBe("Reviewed · 22 Sep 2025");
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
