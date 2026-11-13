// AI contribution: 50% or more AI-generated
import { describe, expect, it } from "vitest";

import { NO_FILTERS } from "../../features/listings/browse";
import { filtersFrom, hasFilters, searchFor, storesOf } from "./browseFilters";

const store = (id: string, name: string) => ({
  id,
  name,
  street_number: "1",
  street_name: "rue Exemple",
  unit: null,
  city: "Montréal",
  postal_code: "H2X 1Y4",
});

describe("browse filters in the page address", () => {
  it("reads every filter, and nothing as no filter", () => {
    expect(filtersFrom(new URLSearchParams("today=1&category=bakery&store=s1"))).toEqual({
      today: true,
      category: "bakery",
      store: "s1",
    });
    expect(filtersFrom(new URLSearchParams(""))).toEqual(NO_FILTERS);
    expect(filtersFrom(new URLSearchParams("today=0&category="))).toEqual(NO_FILTERS);
  });

  it("writes only the filters in use, and reads them back", () => {
    const filters = { today: false, category: "bakery", store: null };
    expect(searchFor(filters).toString()).toBe("category=bakery");
    expect(filtersFrom(searchFor(filters))).toEqual(filters);
    expect(hasFilters(filters)).toBe(true);
    expect(hasFilters(NO_FILTERS)).toBe(false);
  });
});

describe("storesOf", () => {
  it("lists each store of the loaded cards once, by name", () => {
    const card = (id: string, s: ReturnType<typeof store>) => ({ id, store: s }) as never;
    const pages = [
      {
        results: [
          card("1", store("s2", "Épicerie du Quartier")),
          card("2", store("s1", "B.A.D.R.")),
        ],
      },
      { results: [card("3", store("s2", "Épicerie du Quartier"))] },
    ];
    expect(storesOf(pages)).toEqual([
      { value: "s1", label: "B.A.D.R." },
      { value: "s2", label: "Épicerie du Quartier" },
    ]);
    expect(storesOf([])).toEqual([]);
  });
});
