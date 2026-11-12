// AI contribution: 50% or more AI-generated
import { describe, expect, it } from "vitest";

import type { Pickup } from "../../../features/reservations/pickupApi";
import { pickupFactRows } from "./confirmFacts";

const BASE: Pickup = {
  id: "00000000-0000-4000-8000-000000000201",
  status: "reserved",
  holder: null,
  alternate: null,
  title: "Pains",
  unit: "item",
  quantity: 2,
  pickup_code: "P4WZ8H",
  pickup_start: "2026-11-12T20:00:00Z",
  pickup_end: "2026-11-12T23:00:00Z",
  picked_up_at: null,
};

describe("confirmFacts", () => {
  it("omits alternate when absent and uses the unknown-holder fallback", () => {
    const t = (key: string) =>
      ({
        "reservation.confirm.holder": "Titulaire",
        "reservation.confirm.unknownHolder": "Inconnu",
        "reservation.confirm.item": "Article",
        "reservation.confirm.quantity": "Quantité",
        "reservation.confirmation.pickupCode": "Code",
        "reservation.confirmation.pickupWindow": "Fenêtre",
        "listing.units.item": "Article",
      })[key] ?? key;
    const rows = pickupFactRows(
      BASE,
      new Date("2026-11-12T21:00:00Z"),
      "fr",
      { today: "Aujourd'hui", tomorrow: "Demain" },
      t,
    );
    expect(rows.map((row) => row.label)).toEqual([
      "Titulaire",
      "Article",
      "Quantité",
      "Code",
      "Fenêtre",
    ]);
    expect(rows[0]?.value).toBe("Inconnu");
  });

  it("includes alternate and picked-up time when present", () => {
    const t = (key: string) => key;
    const rows = pickupFactRows(
      {
        ...BASE,
        holder: "Fatou D.",
        alternate: "Paul T.",
        picked_up_at: "2026-11-12T21:15:00Z",
      },
      new Date("2026-11-12T21:00:00Z"),
      "en",
      { today: "Today", tomorrow: "Tomorrow" },
      t,
    );
    expect(rows.some((row) => row.value === "Paul T.")).toBe(true);
    expect(rows.some((row) => row.label === "reservation.confirm.pickedUpAt")).toBe(true);
  });
});
