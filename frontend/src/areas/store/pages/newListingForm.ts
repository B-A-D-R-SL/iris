// AI contribution: 50% or more AI-generated
/**
 * Values, defaults and checks of the posting form (forms-and-fields.md, "Listing form").
 * The limits mirror the default `listing_posting` rules; the server stays the
 * authority, and its messages replace these when an active rule version differs.
 */
import dayjs, { type Dayjs } from "dayjs";
import type { ReactNode } from "react";

import type { NewListing } from "../../../features/listings/api";
import {
  allOf,
  hasLength,
  isAcceptedFile,
  isDateInRange,
  isMoneyInRange,
  isRequired,
  validationMessage,
  type Rule,
} from "../../../shared/forms";

export const LIMITS = {
  titleMin: 2,
  titleMax: 80,
  descriptionMax: 500,
  quantityMax: 999,
  maxPerHousehold: 10,
  estimatedValueMaxCents: 100_000,
  startMaxDays: 7,
  minMinutes: 30,
  maxMinutes: 12 * 60,
  photoMaxMb: 5,
} as const;

export const PHOTO_TYPES = ["image/jpeg", "image/png"] as const;

export type PickupDay = "today" | "tomorrow" | "other";

export interface ListingFormValues {
  photo: File | null;
  title: string;
  /** The category's stable code, for example "bakery". */
  category: string;
  description: string;
  quantity: number | string;
  unit: "item" | "bundle";
  maxPerHousehold: number | string;
  day: PickupDay;
  /** "YYYY-MM-DD", only used when `day` is "other". */
  otherDate: string | null;
  /** "HH:mm" in the store's (the browser's) time zone. */
  startTime: string;
  endTime: string;
  bestBefore: string | null;
  estimatedValue: number | null;
  safeAndAllowed: boolean;
}

/** Defaults from forms-and-fields.md: pickup today 16:00 to 18:00, quantity 1, unit item, 1 per household. */
export const DEFAULT_VALUES: ListingFormValues = {
  photo: null,
  title: "",
  category: "",
  description: "",
  quantity: 1,
  unit: "item",
  maxPerHousehold: 1,
  day: "today",
  otherDate: null,
  startTime: "16:00",
  endTime: "18:00",
  bestBefore: null,
  estimatedValue: null,
  safeAndAllowed: false,
};

const DATE = "YYYY-MM-DD";
const TIME = /^([01]\d|2[0-3]):[0-5]\d(:[0-5]\d)?$/;

/** The day chosen with the chips, as YYYY-MM-DD, or null while "other" has no date. */
export function pickupDate(values: Pick<ListingFormValues, "day" | "otherDate">, now: Dayjs) {
  if (values.day === "today") return now.format(DATE);
  if (values.day === "tomorrow") return now.add(1, "day").format(DATE);
  return values.otherDate;
}

/** A local date and "HH:mm" as one moment, or null while either is missing. */
function at(date: string | null, time: string): Dayjs | null {
  if (!date || !TIME.test(time)) return null;
  return dayjs(`${date}T${time}`);
}

function integerIn(min: number, max: number, messageKey: string): Rule<number | string> {
  return (value) => {
    const number = Number(value);
    return value !== "" && Number.isInteger(number) && number >= min && number <= max
      ? null
      : validationMessage(messageKey);
  };
}

const required = isRequired();

/**
 * Rules for @mantine/form. `isFood` tells whether a category code needs a
 * best-before date; `clock` is the current time (replaced in tests).
 */
export function listingRules(isFood: (code: string) => boolean, clock: () => Dayjs = dayjs) {
  return {
    photo: isAcceptedFile({ types: PHOTO_TYPES, maxMb: LIMITS.photoMaxMb }),
    title: allOf(required, hasLength({ min: LIMITS.titleMin, max: LIMITS.titleMax })),
    category: (value: string) =>
      value ? null : validationMessage("store.newListing.categoryError"),
    description: hasLength({ max: LIMITS.descriptionMax }),
    quantity: integerIn(1, LIMITS.quantityMax, "store.newListing.quantityError"),
    maxPerHousehold: integerIn(1, LIMITS.maxPerHousehold, "store.newListing.maxPerHouseholdError"),

    otherDate: (value: string | null, values: ListingFormValues): ReactNode => {
      if (values.day !== "other") return null;
      const now = clock();
      return allOf(
        required,
        isDateInRange({
          min: now.format(DATE),
          max: now.add(LIMITS.startMaxDays, "day").format(DATE),
        }),
      )(value);
    },

    startTime: (value: string, values: ListingFormValues): ReactNode => {
      const now = clock();
      const date = pickupDate(values, now);
      if (!date) return null; // The missing date has its own message.
      const start = at(date, value);
      if (!start) return validationMessage("store.newListing.timeError");
      if (start.isBefore(now)) return validationMessage("store.newListing.startPastError");
      // Elapsed hours, like the server: a daylight-saving change does not stretch the week.
      if (start.isAfter(now.add(LIMITS.startMaxDays * 24, "hour"))) {
        return validationMessage("store.newListing.startTooFarError");
      }
      return null;
    },

    endTime: (value: string, values: ListingFormValues): ReactNode => {
      const date = pickupDate(values, clock());
      const end = at(date, value);
      if (date && !end) return validationMessage("store.newListing.timeError");
      const start = at(date, values.startTime);
      if (!start || !end) return null;
      // Elapsed minutes, so a daylight-saving change counts like the server does.
      const minutes = end.diff(start, "minute");
      return minutes >= LIMITS.minMinutes && minutes <= LIMITS.maxMinutes
        ? null
        : validationMessage("store.newListing.durationError");
    },

    bestBefore: (value: string | null, values: ListingFormValues): ReactNode => {
      if (!isFood(values.category)) return null;
      const invalid = allOf(required, isDateInRange())(value);
      if (invalid) return invalid;
      const pickupEnd = pickupDate(values, clock());
      return pickupEnd && value !== null && value < pickupEnd
        ? validationMessage("store.newListing.bestBeforeError", { date: dayjs(pickupEnd).toDate() })
        : null;
    },

    estimatedValue: isMoneyInRange({ maxCents: LIMITS.estimatedValueMaxCents }),
    safeAndAllowed: (value: boolean) =>
      value ? null : validationMessage("store.newListing.safeAndAllowedError"),
  };
}

/** The request body, from values that passed listingRules. */
export function toNewListing(
  values: ListingFormValues,
  isFood: boolean,
  now: Dayjs = dayjs(),
): NewListing {
  const date = pickupDate(values, now);
  const iso = (time: string) => {
    const moment = at(date, time);
    if (!moment) throw new Error("The pickup date and times were not validated.");
    // "2026-10-29T16:00:00-04:00": the server requires the offset.
    return moment.format();
  };
  const description = values.description.trim();
  return {
    category: values.category,
    title: values.title.trim(),
    description: description || null,
    quantity: Number(values.quantity),
    unit: values.unit,
    max_per_household: Number(values.maxPerHousehold),
    pickup_start: iso(values.startTime),
    pickup_end: iso(values.endTime),
    best_before: isFood ? values.bestBefore : null,
    estimated_value_cents: values.estimatedValue,
    safe_and_allowed: values.safeAndAllowed,
  };
}

/** Which form field shows the server's message for each API field. */
const FORM_FIELD: Record<string, keyof ListingFormValues> = {
  photo: "photo",
  title: "title",
  category: "category",
  description: "description",
  quantity: "quantity",
  unit: "unit",
  max_per_household: "maxPerHousehold",
  pickup_start: "startTime",
  pickup_end: "endTime",
  best_before: "bestBefore",
  estimated_value_cents: "estimatedValue",
  safe_and_allowed: "safeAndAllowed",
};

/** Splits a 400 response into field errors and the messages no field can show. */
export function serverErrors(fields: Record<string, string[]>) {
  const errors: Partial<Record<keyof ListingFormValues, string>> = {};
  const other: string[] = [];
  for (const [apiField, messages] of Object.entries(fields)) {
    const formField = FORM_FIELD[apiField];
    if (formField) errors[formField] = messages.join(" ");
    else other.push(...messages);
  }
  return { errors, other };
}
