// AI contribution: 50% or more AI-generated
/**
 * How listing times, dates and addresses read on the household screens. The API
 * sends UTC; households read Montreal time (docs/03-design/api.md, US-36).
 */
import type { ListingCard } from "../../features/listings/browse";

/** Montreal shares Toronto's IANA time zone. */
export const MONTREAL_TIME_ZONE = "America/Toronto";

export type Language = "fr" | "en";

export interface DayLabels {
  today: string;
  tomorrow: string;
}

const locale = (language: Language) => (language === "fr" ? "fr-CA" : "en-CA");

/** The calendar day of a moment in Montreal, as YYYY-MM-DD. */
export function montrealDate(moment: Date): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: MONTREAL_TIME_ZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(moment);
}

function nextDay(isoDate: string): string {
  const [year, month, day] = isoDate.split("-").map(Number);
  return new Date(Date.UTC(year, month - 1, day + 1)).toISOString().slice(0, 10);
}

/** "16 h" or "16 h 30" in French; "4 p.m." or "4:30 p.m." in English. */
export function formatTime(moment: Date, language: Language): string {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: MONTREAL_TIME_ZONE,
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
    timeZone: MONTREAL_TIME_ZONE,
    hour: "numeric",
    ...(minute ? { minute: "2-digit" } : {}),
  }).format(moment);
}

/** "Aujourd'hui", "Demain", or a short date such as "jeu. 13 nov.", seen from `now`. */
export function formatDay(moment: Date, now: Date, language: Language, labels: DayLabels) {
  const day = montrealDate(moment);
  const today = montrealDate(now);
  if (day === today) return labels.today;
  if (day === nextDay(today)) return labels.tomorrow;
  return new Intl.DateTimeFormat(locale(language), {
    timeZone: MONTREAL_TIME_ZONE,
    weekday: "short",
    day: "numeric",
    month: "short",
  }).format(moment);
}

/** "Aujourd'hui · 16 h – 18 h"; the end gets its own day when the pickup ends after midnight. */
export function formatPickupWindow(
  card: Pick<ListingCard, "pickup_start" | "pickup_end">,
  now: Date,
  language: Language,
  labels: DayLabels,
): string {
  const start = new Date(card.pickup_start);
  const end = new Date(card.pickup_end);
  const endTime = formatTime(end, language);
  const endText =
    montrealDate(start) === montrealDate(end)
      ? endTime
      : `${formatDay(end, now, language, labels)} ${endTime}`;
  return `${formatDay(start, now, language, labels)} · ${formatTime(start, language)} – ${endText}`;
}

/** A calendar date "YYYY-MM-DD" as "11 oct." or, with the year, "11 oct. 2026". */
export function formatDate(isoDate: string, language: Language, withYear = false): string {
  const [year, month, day] = isoDate.split("-").map(Number);
  return new Intl.DateTimeFormat(locale(language), {
    timeZone: "UTC",
    day: "numeric",
    month: "short",
    ...(withYear ? { year: "numeric" } : {}),
  }).format(new Date(Date.UTC(year, month - 1, day)));
}

/** "1234, rue Exemple, Montréal H2X 1Y4"; `unit` is the translated unit, if any. */
export function formatAddress(store: ListingCard["store"], unit: string | null): string {
  const street = `${store.street_number}, ${store.street_name}`;
  return [street, unit, `${store.city} ${store.postal_code}`].filter(Boolean).join(", ");
}
