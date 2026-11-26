// AI contribution: 50% or more AI-generated
import { describe, expect, it, vi } from "vitest";

import { fetchHistoryPage, HistoryFailed, historyUrl } from "./history";

const page = (results: unknown[], next: string | null = null) =>
  Response.json({ count: results.length, next, previous: null, results });

describe("historyUrl", () => {
  it("asks for page 1 without a page number, and later pages with one", () => {
    expect(historyUrl()).toBe("/api/reservations/me/");
    expect(historyUrl(1)).toBe("/api/reservations/me/");
    expect(historyUrl(3)).toBe("/api/reservations/me/?page=3");
  });
});

describe("fetchHistoryPage", () => {
  it("returns a page of reservations, signed in with the session cookie", async () => {
    const fetchMock = vi.fn().mockResolvedValue(page([{ id: "r1", upcoming: true }]));
    vi.stubGlobal("fetch", fetchMock);

    await expect(fetchHistoryPage(2)).resolves.toMatchObject({
      count: 1,
      results: [{ id: "r1", upcoming: true }],
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

  it("refuses a body that is not a page of reservations", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(page([{ id: "r1" }])));

    await expect(fetchHistoryPage()).rejects.toThrow("Invalid reservations API response");
  });
});
