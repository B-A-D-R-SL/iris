// AI contribution: 50% or more AI-generated
import { describe, expect, it, vi } from "vitest";

import { searchFile, searchPage } from "../../test/householdSearch";
import { HouseholdSearchError, searchHouseholds } from "./searchApi";

describe("household search API", () => {
  it("encodes the query and sends the session, language, cache policy and cancellation signal", async () => {
    const fetchMock = vi.fn().mockResolvedValue(Response.json(searchPage()));
    vi.stubGlobal("fetch", fetchMock);
    const controller = new AbortController();
    const page = await searchHouseholds("Élodie + 555", 2, "en", controller.signal);
    expect(page.results[0].id).toBe(searchFile().id);
    const [path, options] = fetchMock.mock.calls[0];
    const url = new URL(path, "http://iris.local");
    expect(url.pathname).toBe("/api/staff/households/");
    expect(url.searchParams.get("q")).toBe("Élodie + 555");
    expect(url.searchParams.get("page")).toBe("2");
    expect(options).toMatchObject({
      credentials: "same-origin",
      cache: "no-store",
      signal: controller.signal,
      headers: { Accept: "application/json", "Accept-Language": "en" },
    });
  });

  it.each([400, 401, 403, 500])(
    "preserves HTTP %s without including private search text in errors",
    async (status) => {
      vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status })));
      const error = await searchHouseholds("private-search", 1, "fr").catch(
        (value: unknown) => value,
      );
      expect(error).toBeInstanceOf(HouseholdSearchError);
      expect(error).toMatchObject({ status });
      expect(String(error)).not.toContain("private-search");
    },
  );

  it.each([
    null,
    [],
    { results: [] },
    searchPage({ count: -1 }),
    searchPage({ results: [{ ...searchFile(), status: "unexpected" } as never] }),
    searchPage({ results: [{ ...searchFile(), phone: null } as never] }),
    { ...searchPage(), next: {} },
  ])("rejects malformed responses", async (body) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json(body)));
    await expect(searchHouseholds("Exemple", 1, "fr")).rejects.toThrow(
      "Invalid household search response",
    );
  });

  it("accepts an empty result page", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(Response.json(searchPage({ count: 0, results: [] }))),
    );
    expect(await searchHouseholds("missing-file", 1, "fr")).toMatchObject({
      count: 0,
      results: [],
    });
  });

  it("lets request cancellation propagate", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new DOMException("Cancelled", "AbortError")));
    await expect(searchHouseholds("Exemple", 1, "fr")).rejects.toMatchObject({
      name: "AbortError",
    });
  });
});
