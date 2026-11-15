// AI contribution: 50% or more AI-generated
/** Store edit form conversions and checks (US-14). */
import { describe, expect, it } from "vitest";

import { demoStore as store } from "../../test/staffStores";
import {
  changedFields,
  completeTime,
  DAYS,
  formatTime,
  hoursErrors,
  toFormValues,
  toHoursValues,
  toOpeningHours,
  type DayValue,
  type Day,
} from "./storeForm";

const OPEN = { open: "08:00", close: "20:00" };

function hours(changes: Partial<Record<Day, DayValue>> = {}): Record<Day, DayValue> {
  return { ...toHoursValues(store.opening_hours), ...changes };
}

describe("toFormValues", () => {
  it("shows empty optional fields as empty text and closed days as closed", () => {
    const values = toFormValues(store);
    expect(values.unit).toBe("");
    expect(values.hours.sun).toEqual({ closed: true, open: "", close: "" });
    expect(values.hours.mon).toEqual({ closed: false, ...OPEN });
  });

  it("starts a store with only notes on empty times to fill in", () => {
    const values = toHoursValues({
      mon: null,
      tue: null,
      wed: null,
      thu: null,
      fri: null,
      sat: null,
      sun: null,
      notes: "Lun-ven 8h-20h",
    });
    expect(DAYS.every((day) => !values[day].closed && values[day].open === "")).toBe(true);
  });
});

describe("hoursErrors", () => {
  it("accepts a full week with closed days", () => {
    expect(hoursErrors(hours())).toEqual({});
  });

  it("needs both times on an open day", () => {
    expect(hoursErrors(hours({ tue: { closed: false, open: "08:00", close: "" } }))).toEqual({
      tue: "required",
    });
  });

  it("needs the closing time after the opening time", () => {
    expect(hoursErrors(hours({ mon: { closed: false, open: "08:00", close: "07:00" } }))).toEqual({
      mon: "closeAfterOpen",
    });
  });

  it("needs at least one open day", () => {
    const closed = Object.fromEntries(
      DAYS.map((day) => [day, { closed: true, open: "", close: "" }]),
    ) as Record<Day, DayValue>;
    expect(hoursErrors(closed)).toEqual({ week: "noOpenDay" });
  });
});

describe("changedFields", () => {
  it("is empty when nothing changed, ignoring spaces and postal code case", () => {
    const initial = toFormValues(store);
    expect(
      changedFields(initial, { ...initial, name: ` ${store.name} `, postal_code: "h2x3k2" }),
    ).toEqual({});
  });

  it("sends only changed fields, trimmed, with blank optional text as null", () => {
    const initial = { ...toFormValues(store), unit: "B" };
    const changes = changedFields(initial, {
      ...initial,
      city: " Laval ",
      unit: "  ",
      postal_code: "h2x1y4",
    });
    expect(changes).toEqual({ city: "Laval", unit: null, postal_code: "H2X 1Y4" });
  });

  it("sends the whole week when one day changes, closed days as null", () => {
    const initial = toFormValues(store);
    const changes = changedFields(initial, {
      ...initial,
      hours: hours({ sat: { closed: false, open: "10:00", close: "18:00" } }),
    });
    expect(changes.opening_hours).toEqual(
      toOpeningHours(hours({ sat: { closed: false, open: "10:00", close: "18:00" } })),
    );
    expect(changes.opening_hours?.sun).toBeNull();
    expect(changes.opening_hours?.sat).toEqual({ open: "10:00", close: "18:00" });
  });
});

describe("typing times", () => {
  it.each([
    ["2000", "20:00"],
    ["20:00", "20:00"],
    ["8", "8"],
    ["083", "08:3"],
    ["20h30", "20:30"],
    ["123456", "12:34"],
  ])("formats %s as %s while typing", (typed, shown) => {
    expect(formatTime(typed)).toBe(shown);
  });

  it.each([
    ["8", "08:00"],
    ["20", "20:00"],
    ["800", "08:00"],
    ["08:3", "08:30"],
    ["930", "09:30"],
    ["20:3", "20:30"],
    ["", ""],
  ])("completes %s as %s on leaving the box", (typed, shown) => {
    expect(completeTime(typed)).toBe(shown);
  });

  it("refuses a time that is not a 24-hour clock time", () => {
    expect(hoursErrors(hours({ wed: { closed: false, open: "25:00", close: "26:00" } }))).toEqual({
      wed: "invalidTime",
    });
  });
});
