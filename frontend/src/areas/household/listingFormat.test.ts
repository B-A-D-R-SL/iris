// AI contribution: 50% or more AI-generated
import { describe, expect, it } from "vitest";

import {
  formatAddress,
  formatDate,
  formatDay,
  formatPickupWindow,
  formatTime,
  montrealDate,
} from "./listingFormat";

// Thursday 12 November 2026, 09:00 in Montreal (UTC-5).
const NOW = new Date("2026-11-12T14:00:00Z");
const LABELS = { today: "Aujourd'hui", tomorrow: "Demain" };

describe("Montreal time", () => {
  it("uses Montreal's calendar day, not UTC's", () => {
    // 23:30 in Montreal is already the next day in UTC.
    expect(montrealDate(new Date("2026-11-13T04:30:00Z"))).toBe("2026-11-12");
  });

  it("writes hours the French way and the English way", () => {
    expect(formatTime(new Date("2026-11-12T21:00:00Z"), "fr")).toBe("16 h");
    expect(formatTime(new Date("2026-11-12T21:30:00Z"), "fr")).toBe("16 h 30");
    expect(formatTime(new Date("2026-11-12T21:00:00Z"), "en")).toBe("4 p.m.");
    expect(formatTime(new Date("2026-11-12T21:30:00Z"), "en")).toBe("4:30 p.m.");
  });

  it("names today and tomorrow, and dates the other days", () => {
    expect(formatDay(new Date("2026-11-12T21:00:00Z"), NOW, "fr", LABELS)).toBe("Aujourd'hui");
    expect(formatDay(new Date("2026-11-13T15:00:00Z"), NOW, "fr", LABELS)).toBe("Demain");
    expect(formatDay(new Date("2026-11-14T15:00:00Z"), NOW, "fr", LABELS)).toBe("sam. 14 nov.");
    expect(formatDay(new Date("2026-11-14T15:00:00Z"), NOW, "en", LABELS)).toMatch(
      /^Sat, Nov\.? 14$/,
    );
  });
});

describe("formatPickupWindow", () => {
  it("reads like the mockups: day · start – end", () => {
    const card = { pickup_start: "2026-11-12T21:00:00Z", pickup_end: "2026-11-12T23:00:00Z" };
    expect(formatPickupWindow(card, NOW, "fr", LABELS)).toBe("Aujourd'hui · 16 h – 18 h");
  });

  it("gives the end its own day when the pickup ends after midnight", () => {
    const card = { pickup_start: "2026-11-13T03:00:00Z", pickup_end: "2026-11-13T06:00:00Z" };
    expect(formatPickupWindow(card, NOW, "fr", LABELS)).toBe("Aujourd'hui · 22 h – Demain 1 h");
  });
});

describe("formatDate and formatAddress", () => {
  it("writes a best-before date without shifting its day", () => {
    expect(formatDate("2026-10-11", "fr")).toBe("11 oct.");
    expect(formatDate("2026-10-11", "fr", true)).toBe("11 oct. 2026");
    expect(formatDate("2026-10-11", "en", true)).toMatch(/^Oct\.? 11, 2026$/);
  });

  it("joins the store address, with its unit when there is one", () => {
    const store = {
      id: "s1",
      name: "Boulangerie du Coin",
      street_number: "1234",
      street_name: "rue Exemple",
      unit: null,
      city: "Montréal",
      postal_code: "H2X 1Y4",
    };
    expect(formatAddress(store, null)).toBe("1234, rue Exemple, Montréal H2X 1Y4");
    expect(formatAddress(store, "local 5")).toBe("1234, rue Exemple, local 5, Montréal H2X 1Y4");
  });
});
