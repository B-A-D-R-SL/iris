// AI contribution: 50% or more AI-generated
import { describe, expect, it } from "vitest";

import { pickedUpWhen } from "./useReservationText";

// Thursday 12 November 2026, 09:00 in Montreal (UTC-5).
const NOW = new Date("2026-11-12T14:00:00Z");

describe("pickedUpWhen (US-48)", () => {
  it("says today with the Montreal time", () => {
    expect(pickedUpWhen(new Date("2026-11-12T13:42:00Z"), NOW, "fr")).toEqual({
      day: "today",
      time: "8 h 42",
    });
  });

  it("says yesterday, even late in the evening that is already tomorrow in UTC", () => {
    // 23:30 on 11 November in Montreal is 04:30 on 12 November in UTC.
    expect(pickedUpWhen(new Date("2026-11-12T04:30:00Z"), NOW, "en")).toEqual({
      day: "yesterday",
      time: "11:30 p.m.",
    });
  });

  it("dates anything older", () => {
    expect(pickedUpWhen(new Date("2026-11-10T22:20:00Z"), NOW, "fr")).toEqual({
      day: "date",
      date: "mar. 10 nov.",
      time: "17 h 20",
    });
  });
});
