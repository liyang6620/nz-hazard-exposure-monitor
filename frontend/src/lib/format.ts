const dateTime = new Intl.DateTimeFormat("en-NZ", {
  timeZone: "Pacific/Auckland",
  day: "numeric",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
  timeZoneName: "short",
});

const integer = new Intl.NumberFormat("en-NZ", { maximumFractionDigits: 0 });
const decimal = new Intl.NumberFormat("en-NZ", {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

export function formatNzDateTime(value: string): string {
  return dateTime.format(new Date(value)).replace("24:", "00:");
}

export function formatInteger(value: number | null): string {
  return value === null ? "Pending" : integer.format(Math.round(value));
}

export function formatDecimal(value: number | null): string {
  return value === null ? "Pending" : decimal.format(value);
}

const eventDisplayNames: Record<string, string> = {
  "Christchurch Feb 2011": "Christchurch, Feb 2011",
  "Christchurch Jun 2011": "Christchurch, Jun 2011",
};

export function displayEventName(name: string): string {
  return eventDisplayNames[name] ?? name;
}

const versionMonths = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];

export function formatSourceVersion(
  version: string | null,
  shakingType: string,
): string {
  if (!version) return "Pending";
  const match = version.match(/^(\d{4}-\d{2}-\d{2})(?:T[^-]+)?-(\w+)$/);
  const label =
    shakingType === "reviewed"
      ? "Reviewed"
      : shakingType === "preliminary"
        ? "Preliminary estimate"
        : "Automatic";
  if (!match) return label;
  const [year, month, day] = match[1].split("-").map(Number);
  return `${label} · ${day} ${versionMonths[month - 1]} ${year}`;
}

export function statusMessage(event: {
  assessment_status: string;
  no_damaging_shaking: boolean;
  assessment_reason?: string;
}): string | null {
  if (event.assessment_status === "outside_model_range")
    return (
      event.assessment_reason ?? "Outside the supported shaking model range"
    );
  if (event.assessment_status === "expired")
    return event.assessment_reason ?? "Outside the 30-day monitoring window";
  if (event.assessment_status === "timed_out")
    return event.assessment_reason ?? "Exposure assessment timed out";
  if (event.assessment_status === "failed")
    return event.assessment_reason ?? "Exposure assessment failed";
  if (event.assessment_status !== "ready") return "Exposure assessment pending";
  if (event.no_damaging_shaking) return "No damaging shaking (MMI < 6)";
  return null;
}

export function formatElapsed(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const remainder = seconds % 60;
  return minutes > 0 ? `${minutes}m ${remainder}s` : `${remainder}s`;
}
