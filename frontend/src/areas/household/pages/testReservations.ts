// AI contribution: 50% or more AI-generated
/** Fake API answers for the pickup history tests (US-48; synthetic data only). */
import { vi } from "vitest";

import type { HistoryEntry } from "../../../features/reservations/history";
import { testUser } from "../../../test/render";
import { CORNER_BAKERY, NEIGHBOURHOOD_GROCERY } from "./testListings";

/** Upcoming: today 16 h – 18 h in Montreal at the corner bakery, with its code. */
export function entry(overrides: Partial<HistoryEntry> = {}): HistoryEntry {
  return {
    id: "00000000-0000-4000-8000-000000000301",
    status: "reserved",
    upcoming: true,
    title: "Pains de la veille",
    unit: "item",
    quantity: 1,
    store: CORNER_BAKERY,
    pickup_start: "2026-11-12T21:00:00Z",
    pickup_end: "2026-11-12T23:00:00Z",
    picked_up_at: null,
    pickup_code: "K7M2QX",
    ...overrides,
  };
}

/** Picked up yesterday at 17 h 20 in Montreal, at the neighbourhood grocery. */
export function pickedUp(overrides: Partial<HistoryEntry> = {}): HistoryEntry {
  return entry({
    id: "00000000-0000-4000-8000-000000000302",
    status: "picked_up",
    upcoming: false,
    title: "Légumes racines",
    quantity: 2,
    store: NEIGHBOURHOOD_GROCERY,
    pickup_start: "2026-11-11T21:00:00Z",
    pickup_end: "2026-11-11T23:00:00Z",
    picked_up_at: "2026-11-11T22:20:00Z",
    pickup_code: null,
    ...overrides,
  });
}

export function historyPage(
  entries: HistoryEntry[],
  { next = null as string | null, count = entries.length } = {},
) {
  return Response.json({ count, next, previous: null, results: entries });
}

/** Fakes /api/me/ (a household's user) and GET /api/reservations/me/. */
export function mockHistoryApi(history: (url: URL) => Response) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const href = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
    const url = new URL(href, "http://localhost");
    if (url.pathname === "/api/me/") return Response.json(testUser("beneficiary"));
    if (url.pathname === "/api/reservations/me/") return history(url);
    return new Response(null, { status: 404 });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

/** The /api/reservations/me/ addresses requested so far, in order. */
export function historyRequests(fetchMock: ReturnType<typeof mockHistoryApi>) {
  return fetchMock.mock.calls
    .map(([input]) => String(input))
    .filter((url) => url.startsWith("/api/reservations/me/"));
}
