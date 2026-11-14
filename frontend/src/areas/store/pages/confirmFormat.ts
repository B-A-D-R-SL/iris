// AI contribution: 50% or more AI-generated
/**
 * Montreal-time pickup window and confirmation time for the store Confirm
 * screen (api.md: times are UTC; staff read America/Montreal).
 */
import type { Pickup } from "../../../features/reservations/pickupApi";

const MONTREAL = "America/Montreal";

export type Language = "fr" | "en";

export interface DayLabels {
  today: string;
  tomorrow: string;
}

/** Calendar day in Montreal as YYYY-MM-DD, from formatToParts (locale-safe). */
export function montrealDate(moment: Date): string {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: MONTREAL,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(moment);
  const year = parts.find((part) => part.type === "year")?.value;
  const month = parts.find((part) => part.type === "month")?.value;
  const day = parts.find((part) => part.type === "day")?.value;
  return `${year}-${month}-${day}`;
}

function nextDay(isoDate: string): string {
  const [year, month, day] = isoDate.split("-").map(Number);
  return new Date(Date.UTC(year, month - 1, day + 1)).toISOString().slice(0, 10);
}

export function formatTime(moment: Date, language: Language): string {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: MONTREAL,
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(moment);
  const hour = Number(parts.find((part) => part.type === "hour")?.value);
  const minute = Number(parts.find((part) => part.type === "minute")?.value);
  if (language === "fr") {
    return minute ? `${hour} h ${String(minute).padStart(2, "0")}` : `${hour} h`;
  }
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: MONTREAL,
    hour: "numeric",
    ...(minute ? { minute: "2-digit" } : {}),
  }).format(moment);
}

function formatDay(moment: Date, now: Date, language: Language, labels: DayLabels) {
  const day = montrealDate(moment);
  const today = montrealDate(now);
  if (day === today) return labels.today;
  if (day === nextDay(today)) return labels.tomorrow;
  return new Intl.DateTimeFormat(language === "fr" ? "fr-CA" : "en-CA", {
    timeZone: MONTREAL,
    weekday: "short",
    day: "numeric",
    month: "short",
  }).format(moment);
}

/** "Aujourd'hui · 15 h – 18 h" for the review and success steps. */
export function pickupWindowText(
  pickup: Pick<Pickup, "pickup_start" | "pickup_end">,
  now: Date,
  language: Language,
  labels: DayLabels,
): string {
  const start = new Date(pickup.pickup_start);
  const end = new Date(pickup.pickup_end);
  const endTime = formatTime(end, language);
  const endText =
    montrealDate(start) === montrealDate(end)
      ? endTime
      : `${formatDay(end, now, language, labels)} ${endTime}`;
  return `${formatDay(start, now, language, labels)} · ${formatTime(start, language)} – ${endText}`;
}

export function pickedUpAtText(iso: string, language: Language): string {
  return formatTime(new Date(iso), language);
}

export function unitLabel(unit: string, t: (key: string) => string): string {
  if (unit === "item") return t("listing.units.item");
  if (unit === "bundle") return t("listing.units.bundle");
  return unit;
}
