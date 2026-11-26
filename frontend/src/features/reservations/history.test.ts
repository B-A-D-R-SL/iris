// AI contribution: 50% or more AI-generated
import { describe, expect, it, vi } from "vitest";

import { fetchHistoryPage, HistoryFailed, historyUrl, nextPageParam } from "./history";

/** A complete entry, as the API sends it (synthetic data). */
const ENTRY = {
  id: "00000000-0000-4000-8000-000000000301",
  status: "reserved",
  upcoming: true,
  title: "Pains de la veille",
  unit: "item",
  quantity: 1,
  store: {
    id: "00000000-0000-4000-8000-0000000000b1",
    name: "Boulangerie du Coin",
    street_number: "1234",
    street_name: "rue Exemple",
    unit: null,
    city: "Montréal",
    postal_code: "H2X 1Y4",
  },
  pickup_start: "2026-11-12T21:00:00Z",
  pickup_end: "2026-11-12T23:00:00Z",
  picked_up_at: null,
  pickup_code: "K7M2QX",
};

/** A copy of `record` without `key`, as a broken API answer would send it. */
function without<T extends object>(record: T, key: keyof T): Partial<T> {
  const copy: Partial<T> = { ...record };
  delete copy[key];
  return copy;
}

const page = (results: unknown[], next: string | null = null) =>
  Response.json({ count: results.length, next, previous: null, results });

describe("historyUrl", () => {
  it("asks for page 1 bare, and later pages with their number and page 1's time", () => {
    expect(historyUrl()).toBe("/api/reservations/me/");
    expect(historyUrl({ page: 1 })).toBe("/api/reservations/me/");
    expect(historyUrl({ page: 3 })).toBe("/api/reservations/me/?page=3");
    expect(historyUrl({ page: 2, asOf: "2026-11-12T14:00:00Z" })).toBe(
      "/api/reservations/me/?page=2&as_of=2026-11-12T14%3A00%3A00Z",
    );
  });
});

describe("nextPageParam", () => {
  it("keeps the page number and as_of of the API's next link", () => {
    expect(
      nextPageParam("http://testserver/api/reservations/me/?as_of=2026-11-12T14%3A00%3A00Z&page=2"),
    ).toEqual({ page: 2, asOf: "2026-11-12T14:00:00Z" });
    expect(nextPageParam("/api/reservations/me/?page=3")).toEqual({ page: 3 });
  });

  it("stops when there is no next page or the link has no usable page", () => {
    expect(nextPageParam(null)).toBeUndefined();
    expect(nextPageParam(undefined)).toBeUndefined();
    expect(nextPageParam("/api/reservations/me/?page=abc")).toBeUndefined();
  });
});

describe("fetchHistoryPage", () => {
  it("returns a page of complete reservations, signed in with the session cookie", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(page([ENTRY, { ...ENTRY, store: { ...ENTRY.store, unit: "5" } }]));
    vi.stubGlobal("fetch", fetchMock);

    await expect(fetchHistoryPage({ page: 2 })).resolves.toMatchObject({
      count: 2,
      results: [ENTRY, { store: { unit: "5" } }],
    });
    expect(fetchMock).toHaveBeenCalledWith("/api/reservations/me/?page=2", {
      headers: { Accept: "application/json" },
      credentials: "same-origin",
    });
  });

  it.each([401, 403, 500])("reports a %i answer with its status", async (status) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status })));

    const error = await fetchHistoryPage().catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(HistoryFailed);
    expect(error).toMatchObject({ status });
  });

  it.each([
    ["only an id and upcoming", { id: ENTRY.id, upcoming: true }],
    ["no store", without(ENTRY, "store")],
    ["a store without its street", { ...ENTRY, store: without(ENTRY.store, "street_name") }],
    ["a quantity as text", { ...ENTRY, quantity: "1" }],
    ["no title", { ...ENTRY, title: undefined }],
  ])("refuses an entry with %s", async (_case, broken) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(page([ENTRY, broken])));

    await expect(fetchHistoryPage()).rejects.toThrow("Invalid reservations API response");
  });
});
