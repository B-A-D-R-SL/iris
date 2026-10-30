// AI contribution: 50% or more AI-generated
import dayjs from "dayjs";
import { isValidElement, type ReactNode } from "react";
import { describe, expect, it } from "vitest";

import {
  DEFAULT_VALUES,
  listingRules,
  pickupDate,
  serverErrors,
  toNewListing,
  type ListingFormValues,
} from "./newListingForm";

// Thursday 12 November 2026, 09:00 in the test machine's time zone: no daylight-saving
// change in the next 7 days, so the limits below hold in any time zone.
const NOW = dayjs("2026-11-12T09:00");
const FOOD = new Set(["bakery"]);
const rules = listingRules(
  (code) => FOOD.has(code),
  () => NOW,
);

const valid: ListingFormValues = {
  ...DEFAULT_VALUES,
  title: "Pains de la veille",
  category: "hygiene",
  safeAndAllowed: true,
};

/** The translation key of a rule's message, or null when the value passes. */
function messageKey(result: ReactNode): string | null {
  if (result === null || result === undefined) return null;
  if (isValidElement<{ messageKey: string }>(result)) return result.props.messageKey;
  throw new Error(`Unexpected rule result: ${String(result)}`);
}

function check(field: keyof typeof rules, changes: Partial<ListingFormValues> = {}) {
  const values = { ...valid, ...changes };
  const rule = rules[field] as (value: unknown, values: ListingFormValues) => ReactNode;
  return messageKey(rule(values[field], values));
}

describe("posting form defaults (forms-and-fields.md)", () => {
  it("starts with pickup today 16:00 to 18:00, quantity 1, unit item and 1 per household", () => {
    expect(DEFAULT_VALUES).toMatchObject({
      day: "today",
      startTime: "16:00",
      endTime: "18:00",
      quantity: 1,
      unit: "item",
      maxPerHousehold: 1,
      safeAndAllowed: false,
    });
  });

  it("turns the day chips into a date", () => {
    expect(pickupDate({ day: "today", otherDate: null }, NOW)).toBe("2026-11-12");
    expect(pickupDate({ day: "tomorrow", otherDate: null }, NOW)).toBe("2026-11-13");
    expect(pickupDate({ day: "other", otherDate: "2026-11-16" }, NOW)).toBe("2026-11-16");
    expect(pickupDate({ day: "other", otherDate: null }, NOW)).toBeNull();
  });
});

describe("posting form rules", () => {
  it("accepts a complete listing", () => {
    for (const field of Object.keys(rules) as (keyof typeof rules)[]) {
      expect(check(field), field).toBeNull();
    }
  });

  it("requires a 2 to 80 character title and a category", () => {
    expect(check("title", { title: "" })).toBe("shared.validation.required");
    expect(check("title", { title: " X " })).toBe("shared.validation.textLength");
    expect(check("title", { title: "x".repeat(81) })).toBe("shared.validation.textLength");
    expect(check("title", { title: "x".repeat(80) })).toBeNull();
    expect(check("category", { category: "" })).toBe("store.newListing.categoryError");
  });

  it("keeps the description to 500 characters", () => {
    expect(check("description", { description: "x".repeat(500) })).toBeNull();
    expect(check("description", { description: "x".repeat(501) })).toBe(
      "shared.validation.textMax",
    );
  });

  it.each([0, 1000, "", 2.5])("refuses the quantity %s", (quantity) => {
    expect(check("quantity", { quantity })).toBe("store.newListing.quantityError");
  });

  it("accepts quantities 1 to 999 and 1 to 10 per household", () => {
    expect(check("quantity", { quantity: 999 })).toBeNull();
    expect(check("maxPerHousehold", { maxPerHousehold: 10 })).toBeNull();
    expect(check("maxPerHousehold", { maxPerHousehold: 11 })).toBe(
      "store.newListing.maxPerHouseholdError",
    );
  });

  it("refuses a pickup that already started or starts more than 7 days ahead", () => {
    expect(check("startTime", { startTime: "08:59" })).toBe("store.newListing.startPastError");
    expect(check("startTime", { startTime: "09:00" })).toBeNull();
    const inSevenDays = { day: "other" as const, otherDate: "2026-11-19" };
    expect(check("startTime", { ...inSevenDays, startTime: "09:00" })).toBeNull();
    expect(check("startTime", { ...inSevenDays, startTime: "09:01" })).toBe(
      "store.newListing.startTooFarError",
    );
  });

  it("asks for a date when 'Autre date' is chosen, within 7 days", () => {
    expect(check("otherDate", { day: "other", otherDate: null })).toBe(
      "shared.validation.required",
    );
    expect(check("otherDate", { day: "other", otherDate: "2026-11-20" })).toBe(
      "shared.validation.dateMax",
    );
    expect(check("otherDate", { day: "other", otherDate: "2026-11-11" })).toBe(
      "shared.validation.dateMin",
    );
    // The start time waits for the date instead of repeating its error.
    expect(check("startTime", { day: "other", otherDate: null })).toBeNull();
  });

  it("keeps the pickup between 30 minutes and 12 hours", () => {
    expect(check("endTime", { endTime: "16:29" })).toBe("store.newListing.durationError");
    expect(check("endTime", { endTime: "16:30" })).toBeNull();
    expect(check("endTime", { startTime: "10:00", endTime: "22:00" })).toBeNull();
    expect(check("endTime", { startTime: "10:00", endTime: "22:01" })).toBe(
      "store.newListing.durationError",
    );
    expect(check("endTime", { endTime: "15:00" })).toBe("store.newListing.durationError");
    expect(check("endTime", { endTime: "" })).toBe("store.newListing.timeError");
  });

  it("asks for a best-before date on or after the pickup day, for food only", () => {
    expect(check("bestBefore", { category: "hygiene", bestBefore: null })).toBeNull();
    expect(check("bestBefore", { category: "bakery", bestBefore: null })).toBe(
      "shared.validation.required",
    );
    expect(check("bestBefore", { category: "bakery", bestBefore: "2026-11-11" })).toBe(
      "store.newListing.bestBeforeError",
    );
    expect(check("bestBefore", { category: "bakery", bestBefore: "2026-11-12" })).toBeNull();
    expect(
      check("bestBefore", { category: "bakery", day: "tomorrow", bestBefore: "2026-11-12" }),
    ).toBe("store.newListing.bestBeforeError");
  });

  it("limits the photo and the estimated value, and requires the confirmation", () => {
    const gif = new File(["gif"], "pain.gif", { type: "image/gif" });
    expect(check("photo", { photo: gif })).toBe("shared.validation.fileType");
    expect(check("estimatedValue", { estimatedValue: 100_000 })).toBeNull();
    expect(check("estimatedValue", { estimatedValue: 100_001 })).toBe(
      "shared.validation.moneyRange",
    );
    expect(check("safeAndAllowed", { safeAndAllowed: false })).toBe(
      "store.newListing.safeAndAllowedError",
    );
  });
});

describe("toNewListing", () => {
  it("sends the category code and local pickup times with their offset", () => {
    const body = toNewListing({ ...valid, title: "  Pains  ", description: "  " }, false, NOW);

    expect(body).toMatchObject({
      category: "hygiene",
      title: "Pains",
      description: null,
      quantity: 1,
      unit: "item",
      max_per_household: 1,
      best_before: null,
      estimated_value_cents: null,
      safe_and_allowed: true,
    });
    expect(body.pickup_start).toMatch(/^2026-11-12T16:00:00[+-]\d{2}:\d{2}$/);
    expect(new Date(body.pickup_start).getTime()).toBe(new Date(2026, 10, 12, 16).getTime());
    expect(new Date(body.pickup_end).getTime()).toBe(new Date(2026, 10, 12, 18).getTime());
  });

  it("uses the chosen day and keeps the best-before date only for food", () => {
    const values = { ...valid, day: "tomorrow" as const, bestBefore: "2026-11-14" };
    expect(toNewListing(values, true, NOW)).toMatchObject({
      pickup_start: expect.stringMatching(/^2026-11-13T16:00/),
      best_before: "2026-11-14",
    });
    expect(toNewListing(values, false, NOW).best_before).toBeNull();
  });
});

describe("serverErrors", () => {
  it("puts each API field's messages under its form field", () => {
    expect(
      serverErrors({
        pickup_end: ["The pickup must last 30 to 720 minutes."],
        max_per_household: ["Too many."],
        non_field_errors: ["Something else."],
      }),
    ).toEqual({
      errors: {
        endTime: "The pickup must last 30 to 720 minutes.",
        maxPerHousehold: "Too many.",
      },
      other: ["Something else."],
    });
  });
});
