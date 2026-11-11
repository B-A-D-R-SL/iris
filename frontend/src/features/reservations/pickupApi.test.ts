// AI contribution: 50% or more AI-generated
import { afterEach, describe, expect, it, vi } from "vitest";

import { confirmPickup, lookupPickup, PickupFailed } from "./pickupApi";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("pickupApi", () => {
  it("posts a lookup and a confirm with the CSRF token", async () => {
    document.cookie = "csrftoken=ready; path=/";
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/lookup/")) {
        expect(init?.headers).toMatchObject({
          "X-CSRFToken": "ready",
          "Accept-Language": "fr",
        });
        expect(JSON.parse(String(init?.body))).toEqual({ code: "P4WZ8H" });
        return Response.json({
          id: "1",
          status: "reserved",
          holder: "Fatou D.",
          alternate: null,
          title: "Pain",
          unit: "item",
          quantity: 1,
          pickup_code: "P4WZ8H",
          pickup_start: "2026-11-12T20:00:00Z",
          pickup_end: "2026-11-12T23:00:00Z",
          picked_up_at: null,
        });
      }
      expect(url).toContain("/api/store/pickups/1/confirm/");
      expect(init?.body).toBeUndefined();
      return Response.json({
        id: "1",
        status: "picked_up",
        holder: "Fatou D.",
        alternate: null,
        title: "Pain",
        unit: "item",
        quantity: 1,
        pickup_code: "P4WZ8H",
        pickup_start: "2026-11-12T20:00:00Z",
        pickup_end: "2026-11-12T23:00:00Z",
        picked_up_at: "2026-11-12T21:00:00Z",
      });
    });
    vi.stubGlobal("fetch", fetchMock);

    const found = await lookupPickup("P4WZ8H", "fr");
    expect(found.holder).toBe("Fatou D.");
    const done = await confirmPickup("1", "fr");
    expect(done.status).toBe("picked_up");
  });

  it("surfaces refusal codes from the API", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        Response.json({ code: "unknown_code", message: "missing", fields: {} }, { status: 404 }),
      ),
    );
    await expect(lookupPickup("ZZZZZZ", "en")).rejects.toMatchObject({
      name: "PickupFailed",
      code: "unknown_code",
      status: 404,
    } satisfies Partial<PickupFailed>);
  });
});
