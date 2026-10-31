/**
 * AI contribution: 50% or more AI-generated
 * Tests for the public Categories API client.
 */

import { describe, expect, it, vi } from "vitest";

import { getCategories } from "./api";

const bakery = {
  code: "bakery",
  name_fr: "Boulangerie",
  name_en: "Bakery",
  is_food: true,
  default_value_cents: 400,
};

describe("getCategories", () => {
  it("returns valid categories", async () => {
    const fetchMock = vi.fn().mockResolvedValue(Response.json([bakery]));
    vi.stubGlobal("fetch", fetchMock);

    await expect(getCategories()).resolves.toEqual([bakery]);
    expect(fetchMock).toHaveBeenCalledWith("/api/categories/");
  });

  it("accepts an empty category list", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json([])));

    await expect(getCategories()).resolves.toEqual([]);
  });

  it("rejects unsuccessful HTTP responses", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 503 })));

    await expect(getCategories()).rejects.toThrow("Failed to fetch categories: 503");
  });

  it("rejects malformed API responses", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json([{ code: "bakery" }])));

    await expect(getCategories()).rejects.toThrow("Invalid categories API response");
  });

  it("rejects negative or fractional cent values", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(Response.json([{ ...bakery, default_value_cents: -100 }])),
    );

    await expect(getCategories()).rejects.toThrow("Invalid categories API response");

    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(Response.json([{ ...bakery, default_value_cents: 4.5 }])),
    );

    await expect(getCategories()).rejects.toThrow("Invalid categories API response");
  });
});
