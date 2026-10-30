// AI contribution: 50% or more AI-generated
/**
 * Values, defaults and checks of the posting form (forms-and-fields.md, "Listing form").
 * Only required fields and formats are checked here. Posting limits and safety
 * decisions belong to the API; its 400 messages appear on the matching fields.
 */
import dayjs, { type Dayjs } from "dayjs";
import type { ReactNode } from "react";

import type { NewListing } from "../../../features/listings/api";
import {
  allOf,
  isAcceptedFile,
  isDateInRange,
  isRequired,
  validationMessage,
  type Rule,
} from "../../../shared/forms";

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

function integerFormat(): Rule<number | string> {
  return (value) => {
    const number = Number(value);
    return String(value).trim() !== "" && Number.isSafeInteger(number)
      ? null
      : validationMessage("shared.validation.integer");
  };
}

const required = isRequired();

/**
 * Rules for @mantine/form. `isFood` tells whether a category code needs a
 * best-before date. Date ordering and pickup limits are checked by the API.
 */
export function listingRules(isFood: (code: string) => boolean) {
  return {
    photo: isAcceptedFile({ types: PHOTO_TYPES }),
    title: required,
    category: (value: string) =>
      value ? null : validationMessage("store.newListing.categoryError"),
    quantity: integerFormat(),
    maxPerHousehold: integerFormat(),

    otherDate: (value: string | null, values: ListingFormValues): ReactNode => {
      if (values.day !== "other") return null;
      return allOf(required, isDateInRange())(value);
    },

    startTime: (value: string): ReactNode =>
      TIME.test(value) ? null : validationMessage("store.newListing.timeError"),

    endTime: (value: string): ReactNode =>
      TIME.test(value) ? null : validationMessage("store.newListing.timeError"),

    bestBefore: (value: string | null, values: ListingFormValues): ReactNode => {
      if (!isFood(values.category)) return null;
      return allOf(required, isDateInRange())(value);
    },

    estimatedValue: (value: number | null): ReactNode =>
      value === null || Number.isSafeInteger(value)
        ? null
        : validationMessage("shared.validation.integer"),
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
