// AI contribution: 50% or more AI-generated
/**
 * Store edit form values (US-14): conversions between the API store and what
 * the admin types, the opening-hours checks, and the PATCH body of only the
 * fields that changed. No React here, so it is easy to test. The server checks
 * every rule again (BR-STORE-001, BR-STORE-006).
 */
import { normalizePostalCode } from "../../shared/forms/formats";
import type { OpeningHours, StaffStore, StoreChanges } from "./adminApi";

export const DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"] as const;
export type Day = (typeof DAYS)[number];

export interface DayValue {
  closed: boolean;
  open: string;
  close: string;
}

export interface StoreFormValues {
  name: string;
  street_number: string;
  street_name: string;
  unit: string;
  city: string;
  postal_code: string;
  phone: string;
  email: string;
  pickup_instructions: string;
  hours: Record<Day, DayValue>;
}

const TEXT_FIELDS = [
  "name",
  "street_number",
  "street_name",
  "city",
  "phone",
  "email",
] as const satisfies readonly (keyof StoreFormValues & keyof StoreChanges)[];
const OPTIONAL_FIELDS = ["unit", "pickup_instructions"] as const;

/** The schedule as the form shows it. A store with no schedule yet (only
 * free-text notes, or nothing) starts with empty times to fill in. */
export function toHoursValues(hours: OpeningHours): Record<Day, DayValue> {
  const hasSchedule = DAYS.some((day) => hours[day] != null);
  const values = {} as Record<Day, DayValue>;
  for (const day of DAYS) {
    const range = hours[day];
    values[day] = range
      ? { closed: false, open: range.open, close: range.close }
      : { closed: hasSchedule, open: "", close: "" };
  }
  return values;
}

export function toFormValues(store: StaffStore): StoreFormValues {
  return {
    name: store.name,
    street_number: store.street_number,
    street_name: store.street_name,
    unit: store.unit ?? "",
    city: store.city,
    postal_code: store.postal_code,
    phone: store.phone,
    email: store.email,
    pickup_instructions: store.pickup_instructions ?? "",
    hours: toHoursValues(store.opening_hours),
  };
}

/** Closed days are null; notes are read-only on the server and never sent. */
export function toOpeningHours(hours: Record<Day, DayValue>): OpeningHours {
  const result = { notes: null } as OpeningHours;
  for (const day of DAYS) {
    const value = hours[day];
    result[day] = value.closed ? null : { open: value.open, close: value.close };
  }
  return result;
}

export type HoursError = "required" | "invalidTime" | "closeAfterOpen";

/** Form error that only marks the grid; each day shows its own message. */
export const HOURS_INVALID = "hours_invalid";

const TIME = /^(?:[01]\d|2[0-3]):[0-5]\d$/;

/** What the admin types, as 24-hour "HH:MM": "2000" -> "20:00", "8" stays "8". */
export function formatTime(input: string): string {
  const digits = input.replace(/\D/g, "").slice(0, 4);
  return digits.length <= 2 ? digits : `${digits.slice(0, 2)}:${digits.slice(2)}`;
}

/**
 * On leaving the box: "8" -> "08:00", "20" -> "20:00", "08:3" -> "08:30",
 * "800" -> "08:00", "930" -> "09:30". Three digits keep the first two as the
 * hour when they make one (and the minutes can start with the third digit).
 */
export function completeTime(value: string): string {
  const digits = value.replace(/\D/g, "");
  if (digits.length === 0) return "";
  if (digits.length <= 2) return `${digits.padStart(2, "0")}:00`;
  if (digits.length === 3) {
    const twoDigitHour = Number(digits.slice(0, 2)) <= 23 && Number(digits[2]) <= 5;
    return formatTime(twoDigitHour ? `${digits}0` : `0${digits}`);
  }
  return formatTime(digits);
}

/** Error keys (storeAdmin.hours.*) by day, plus "noOpenDay" for the week. */
export function hoursErrors(
  hours: Record<Day, DayValue>,
): Partial<Record<Day, HoursError>> & { week?: "noOpenDay" } {
  const errors: Partial<Record<Day, HoursError>> & { week?: "noOpenDay" } = {};
  for (const day of DAYS) {
    const { closed, open, close } = hours[day];
    if (closed) continue;
    if (!open || !close) errors[day] = "required";
    else if (!TIME.test(open) || !TIME.test(close)) errors[day] = "invalidTime";
    // "HH:MM" strings compare in time order.
    else if (close <= open) errors[day] = "closeAfterOpen";
  }
  if (DAYS.every((day) => hours[day].closed)) errors.week = "noOpenDay";
  return errors;
}

function sameHours(a: Record<Day, DayValue>, b: Record<Day, DayValue>): boolean {
  return JSON.stringify(toOpeningHours(a)) === JSON.stringify(toOpeningHours(b));
}

/** Only what changed, cleaned the way the server stores it. */
export function changedFields(
  initial: StoreFormValues,
  values: StoreFormValues,
): Partial<StoreChanges> {
  const changes: Partial<StoreChanges> = {};
  for (const field of TEXT_FIELDS) {
    if (values[field].trim() !== initial[field].trim()) changes[field] = values[field].trim();
  }
  for (const field of OPTIONAL_FIELDS) {
    const value = values[field].trim();
    if (value !== initial[field].trim()) changes[field] = value || null;
  }
  const postal = normalizePostalCode(values.postal_code);
  if (postal !== normalizePostalCode(initial.postal_code)) changes.postal_code = postal;
  if (!sameHours(initial.hours, values.hours)) changes.opening_hours = toOpeningHours(values.hours);
  return changes;
}

/** One day as the server stores it, so blank and closed compare the same way. */
function dayKey(value: DayValue): string {
  return value.closed ? "closed" : `${value.open}-${value.close}`;
}

/**
 * Names of the fields that differ from the saved store (``hours.mon`` and so on
 * for single days), to mark them as changed but not saved yet.
 */
export function modifiedFields(initial: StoreFormValues, values: StoreFormValues): Set<string> {
  const modified = new Set<string>(
    Object.keys(changedFields(initial, values)).filter((field) => field !== "opening_hours"),
  );
  for (const day of DAYS) {
    if (dayKey(initial.hours[day]) !== dayKey(values.hours[day])) modified.add(`hours.${day}`);
  }
  return modified;
}

/** Marks a label with "*" while its field has changes that are not saved. */
export function markModified(label: string, modified: boolean): string {
  return modified ? label + " *" : label;
}
