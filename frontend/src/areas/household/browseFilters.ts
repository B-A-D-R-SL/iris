// AI contribution: 50% or more AI-generated
/** The browse filters in the page address, and the store choices (US-36). */
import type { Category } from "../../features/categories/api";
import type { BrowseFilters, ListingPage } from "../../features/listings/browse";
import type { FilterGroup } from "./components/FilterSheet";

/** ?today=1&category=bakery&store=<id>; anything missing means "any". */
export function filtersFrom(params: URLSearchParams): BrowseFilters {
  return {
    today: params.get("today") === "1",
    category: params.get("category") || null,
    store: params.get("store") || null,
  };
}

/** The address for these filters; filters not in use are left out. */
export function searchFor(filters: BrowseFilters): URLSearchParams {
  const params = new URLSearchParams();
  if (filters.today) params.set("today", "1");
  if (filters.category) params.set("category", filters.category);
  if (filters.store) params.set("store", filters.store);
  return params;
}

export function hasFilters(filters: BrowseFilters): boolean {
  return filters.today || filters.category !== null || filters.store !== null;
}

/**
 * The stores of the pages loaded so far, by name, once each. Households have
 * no store list, so a store appears once one of its listings has loaded.
 */
export function storesOf(pages: readonly Pick<ListingPage, "results">[]) {
  const names = new Map<string, string>();
  for (const page of pages) {
    for (const card of page.results) names.set(card.store.id, card.store.name);
  }
  return [...names]
    .map(([value, label]) => ({ value, label }))
    .sort((a, b) => a.label.localeCompare(b.label));
}

/** The category sheet's groups: food first, each sorted by name, empty groups left out. */
export function categoryGroupsOf(
  categories: readonly Category[],
  nameOf: (code: string) => string,
  labels: { food: string; other: string },
): FilterGroup[] {
  return [true, false]
    .map((food) => ({
      label: food ? labels.food : labels.other,
      options: categories
        .filter((category) => category.is_food === food)
        .map((category) => ({ value: category.code, label: nameOf(category.code) }))
        .sort((a, b) => a.label.localeCompare(b.label)),
    }))
    .filter((group) => group.options.length > 0);
}
