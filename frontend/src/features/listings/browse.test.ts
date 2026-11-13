// AI contribution: 50% or more AI-generated
import { describe, expect, it, vi } from "vitest";

import {
  browseUrl,
  BrowseFailed,
  fetchListingPage,
  findListingCard,
  NO_FILTERS,
  NOT_APPROVED,
} from "./browse";

const card = (id: string) => ({ id, title: `Offre ${id}` });
const page = (ids: string[], next: string | null = null) =>
  Response.json({ count: ids.length, next, previous: null, results: ids.map(card) });

describe("browseUrl", () => {
  it("sends only the filters in use", () => {
    expect(browseUrl(NO_FILTERS)).toBe("/api/listings/");
    expect(browseUrl({ today: true, category: "bakery", store: "s1" }, 2)).toBe(
      "/api/listings/?today=true&category=bakery&store=s1&page=2",
    );
  });
});

describe("fetchListingPage", () => {
  it("returns a page of cards", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(page(["a"])));
    await expect(fetchListingPage(NO_FILTERS)).resolves.toMatchObject({
      count: 1,
      results: [{ id: "a" }],
    });
  });

  it("reports a household that is not approved with the API's code", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          Response.json(
            { code: NOT_APPROVED, message: "Seuls les foyers approuvés…", fields: {} },
            { status: 403 },
          ),
        ),
    );
    const error = await fetchListingPage(NO_FILTERS).catch((caught: unknown) => caught);
    expect(error).toBeInstanceOf(BrowseFailed);
    expect(error).toMatchObject({ status: 403, code: NOT_APPROVED });
  });

  it("refuses a failure without a body and an unexpected answer", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("Bad gateway", { status: 502 })));
    await expect(fetchListingPage(NO_FILTERS)).rejects.toMatchObject({ status: 502, code: "" });

    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json({ results: "nope" })));
    await expect(fetchListingPage(NO_FILTERS)).rejects.toThrow("Invalid listings API response");
  });
});

describe("findListingCard", () => {
  it("reads the unfiltered pages until it finds the listing", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(page(["a", "b"], "http://testserver/api/listings/?page=2"))
      .mockResolvedValueOnce(page(["c"]));
    vi.stubGlobal("fetch", fetchMock);

    await expect(findListingCard("c")).resolves.toMatchObject({ id: "c" });
    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
      "/api/listings/",
      "/api/listings/?page=2",
    ]);
  });

  it("returns null when the listing is not visible (any more)", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(page(["a"])));
    await expect(findListingCard("gone")).resolves.toBeNull();
  });
});
