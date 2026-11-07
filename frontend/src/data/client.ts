import type {
  EventSummary,
  HousekeepingHeartbeat,
  Manifest,
  SiteData,
} from "./types";

async function readJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(path, { signal, cache: "no-cache" });
  if (!response.ok)
    throw new Error(`Website data request failed (${response.status})`);
  return (await response.json()) as T;
}

export async function loadSiteData(signal?: AbortSignal): Promise<SiteData> {
  const manifest = await readJson<Manifest>("/data/manifest.json", signal);
  const [events, heartbeat] = await Promise.all([
    readJson<SiteData["events"]>(`${manifest.base_path}/events.json`, signal),
    loadHousekeepingHeartbeat(signal),
  ]);
  return { manifest, events, heartbeat };
}

export async function loadHousekeepingHeartbeat(
  signal?: AbortSignal,
): Promise<HousekeepingHeartbeat | null> {
  if (
    !window.location.hostname.endsWith(".web.core.windows.net") &&
    import.meta.env.VITE_PUBLIC_HEARTBEAT !== "true"
  )
    return null;
  try {
    const record = await readJson<HousekeepingHeartbeat>(
      "/data/housekeeping.json",
      signal,
    );
    if (record.status !== "success" || !record.completed_at) return null;
    return record;
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError")
      throw error;
    return null;
  }
}

export async function loadEventSummary(
  basePath: string,
  eventId: string,
  signal?: AbortSignal,
): Promise<EventSummary> {
  return readJson<EventSummary>(
    `${basePath}/events/${encodeURIComponent(eventId)}/summary.json`,
    signal,
  );
}

export async function loadReplaySummary(
  basePath: string,
  eventId: string,
  signal?: AbortSignal,
): Promise<EventSummary> {
  return readJson<EventSummary>(
    `${basePath}/replays/${encodeURIComponent(eventId)}/summary.json`,
    signal,
  );
}

export function eventExposureUrl(basePath: string, eventId: string): string {
  return `${basePath}/events/${encodeURIComponent(eventId)}/exposure.geojson`;
}

export function replayExposureUrl(basePath: string, eventId: string): string {
  return `${basePath}/replays/${encodeURIComponent(eventId)}/exposure.geojson`;
}
