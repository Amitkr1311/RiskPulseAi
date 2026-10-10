export function formatNumber(value: number | string | null | undefined, maximumFractionDigits = 0): string {
  if (value === null || value === undefined || value === "") return "Not available";
  const numeric = typeof value === "string" ? Number(value) : value;
  if (!Number.isFinite(numeric)) return "Not available";
  return new Intl.NumberFormat("en-IN", { maximumFractionDigits }).format(numeric);
}

export function formatInr(value: number | string | null | undefined, unit?: "crore"): string {
  if (value === null || value === undefined || value === "") return "Not available";
  const numeric = typeof value === "string" ? Number(value) : value;
  if (!Number.isFinite(numeric)) return "Not available";
  return unit === "crore"
    ? `₹${new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2 }).format(numeric)} crore`
    : `₹${new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2 }).format(numeric)}`;
}

export function formatPercent(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === "") return "Not available";
  const numeric = typeof value === "string" ? Number(value) : value;
  if (!Number.isFinite(numeric)) return "Not available";
  return `${new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2 }).format(numeric)}%`;
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "Not available";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Not available";
  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

export function formatRelative(value: string | null | undefined): string {
  if (!value) return "Not available";
  const timestamp = new Date(value).getTime();
  if (!Number.isFinite(timestamp)) return "Not available";
  const minutes = Math.round((timestamp - Date.now()) / 60_000);
  const formatter = new Intl.RelativeTimeFormat("en", { numeric: "auto" });
  if (Math.abs(minutes) < 60) return formatter.format(minutes, "minute");
  return formatter.format(Math.round(minutes / 60), "hour");
}

export function titleCase(value: string): string {
  return value.replace(/[_-]+/g, " ").replace(/\s+/g, " ").trim().replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function cleanText(value: string | null | undefined): string {
  if (!value) return "Not available";
  const withoutTags = value
    .replace(/<script[\s\S]*?<\/script>/gi, " ")
    .replace(/<style[\s\S]*?<\/style>/gi, " ")
    .replace(/<[^>]*>/g, " ");
  return withoutTags
    .replace(/&amp;/gi, "&")
    .replace(/&quot;/gi, '"')
    .replace(/&#39;/gi, "'")
    .replace(/&lt;/gi, "<")
    .replace(/&gt;/gi, ">")
    .replace(/&#(\d+);/g, (_match, code: string) => String.fromCodePoint(Number(code)))
    .replace(/\s+/g, " ")
    .trim() || "Not available";
}
