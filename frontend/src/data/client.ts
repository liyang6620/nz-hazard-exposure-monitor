import type { EventSummary, Manifest, SiteData } from "./types";

async function readJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(path, { signal, cache: "no-cache" });
  if (!response.ok)
    throw new Error(`Website data request failed (${response.status})`);
  return (await response.json()) as T;
}

export async function loadSiteData(signal?: AbortSignal): Promise<SiteData> {
  const manifest = await readJson<Manifest>("/data/manifest.json", signal);
  const events = await readJson<SiteData["events"]>(
    `${manifest.base_path}/events.json`,
    signal,
  );
  return { manifest, events };
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
