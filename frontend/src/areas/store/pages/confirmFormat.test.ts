// AI contribution: 50% or more AI-generated
import { describe, expect, it } from "vitest";

import { formatTime, pickedUpAtText, pickupWindowText, unitLabel } from "./confirmFormat";

describe("confirmFormat", () => {
  it("formats Montreal pickup windows and confirmation times", () => {
    const labels = { today: "Aujourd'hui", tomorrow: "Demain" };
    const now = new Date("2026-11-12T18:00:00Z");
    expect(
      pickupWindowText(
        { pickup_start: "2026-11-12T20:00:00Z", pickup_end: "2026-11-12T23:00:00Z" },
        now,
        "fr",
        labels,
      ),
    ).toBe("Aujourd'hui · 15 h – 18 h");
    expect(formatTime(new Date("2026-11-12T20:30:00Z"), "fr")).toBe("15 h 30");
    expect(pickedUpAtText("2026-11-12T20:30:00Z", "en")).toBe("3:30 p.m.");
  });

  it("translates listing units", () => {
    const t = (key: string) =>
      key === "listing.units.item" ? "Article" : key === "listing.units.bundle" ? "Lot" : key;
    expect(unitLabel("item", t)).toBe("Article");
    expect(unitLabel("bundle", t)).toBe("Lot");
    expect(unitLabel("crate", t)).toBe("crate");
  });

  it("labels tomorrow and later Montreal days, and English times without minutes", () => {
    const labels = { today: "Today", tomorrow: "Tomorrow" };
    const now = new Date("2026-11-12T18:00:00Z");
    expect(
      pickupWindowText(
        { pickup_start: "2026-11-13T20:00:00Z", pickup_end: "2026-11-13T23:00:00Z" },
        now,
        "en",
        labels,
      ),
    ).toMatch(/^Tomorrow · /);
    expect(
      pickupWindowText(
        { pickup_start: "2026-11-15T20:00:00Z", pickup_end: "2026-11-16T01:00:00Z" },
        now,
        "en",
        labels,
      ),
    ).toMatch(/Sun/);
    expect(formatTime(new Date("2026-11-12T20:00:00Z"), "en")).toMatch(/3\s?p\.?m\.?/i);
  });
});
