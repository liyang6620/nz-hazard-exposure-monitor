export type AssessmentStatus =
  | "ready"
  | "processing"
  | "outside_model_range"
  | "expired"
  | "timed_out"
  | "failed";

export interface ProcessingRecord {
  event_id: string;
  earthquake_at: string;
  published_at: string;
  elapsed_seconds: number;
}

export interface Manifest {
  schema_version: number;
  generation_id: string;
  generated_at: string;
  latest_event_id: string | null;
  featured_event_id: string | null;
  base_path: string;
  processing_record?: ProcessingRecord | null;
}

export interface BriefingState {
  status: "pending" | "approved" | "rejected" | "expired";
  title: string | null;
  public_path: string | null;
}

export interface EventListItem {
  event_id: string;
  name: string;
  origin_time: string;
  magnitude: number;
  depth_km: number;
  latitude: number;
  longitude: number;
  assessment_status: AssessmentStatus;
  assessment_reason?: string;
  max_mmi: number | null;
  buildings_mmi_ge_6: number | null;
  population_mmi_ge_6: number | null;
  no_damaging_shaking: boolean;
  mmi_source: string | null;
  source_kind: "official" | "preliminary";
  source_version: string | null;
  shaking_type: string;
  event_time_status: string;
  as_if_today: boolean;
  is_recent_monitoring: boolean;
  is_historical_replay: boolean;
  most_affected_region?: string | null;
  map_summary: string;
  briefing: BriefingState;
}

export interface MmiBand {
  mmi_band: string;
  buildings: number;
  population: number;
}

export interface RegionExposure {
  region_code: string;
  region_name: string;
  buildings: number;
  population: number;
}

export interface EventSummary extends EventListItem {
  mmi_bands: MmiBand[];
  regions: RegionExposure[];
}

export interface SiteData {
  manifest: Manifest;
  events: EventListItem[];
}
