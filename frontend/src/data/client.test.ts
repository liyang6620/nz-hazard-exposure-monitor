import { afterEach, describe, expect, it, vi } from "vitest";

import { loadHousekeepingHeartbeat } from "./client";

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe("loadHousekeepingHeartbeat", () => {
  it("reads the completed Azure check without relying on manifest age", async () => {
    vi.stubEnv("VITE_PUBLIC_HEARTBEAT", "true");
    const fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        completed_at: "2026-11-06T02:00:12Z",
        status: "success",
        data_unchanged: true,
        build_sha: "tested-build",
        site_generation: "test",
      }),
    });
    vi.stubGlobal("fetch", fetch);

    expect((await loadHousekeepingHeartbeat())?.data_unchanged).toBe(true);
    expect(fetch).toHaveBeenCalledWith("/data/housekeeping.json", {
      signal: undefined,
      cache: "no-cache",
    });
  });

  it("does not show a failed check as the last successful one", async () => {
    vi.stubEnv("VITE_PUBLIC_HEARTBEAT", "true");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          status: "failed",
          completed_at: "2026-11-06T02:00:12Z",
        }),
      }),
    );
    expect(await loadHousekeepingHeartbeat()).toBeNull();
  });
});
