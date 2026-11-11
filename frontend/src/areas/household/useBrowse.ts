// AI contribution: 50% or more AI-generated
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router";

import { getCategories } from "../../features/categories/api";
import { useListings, type BrowseFilters } from "../../features/listings/browse";
import { categoryGroupsOf, filtersFrom, hasFilters, searchFor, storesOf } from "./browseFilters";
import { useListingText } from "./useListingText";

/**
 * The browse screen's state (US-36): the filters kept in the address, the
 * listing pages, and what the chips and the filter sheets offer.
 */
export function useBrowse() {
  const { t } = useTranslation();
  const text = useListingText();
  const [params, setParams] = useSearchParams();
  const filters = filtersFrom(params);
  const listings = useListings(filters);
  // The store choices come from the same list without the store filter, so
  // choosing a store does not hide the others (the same query when none is chosen).
  const storeSource = useListings({ ...filters, store: null });
  const categories = useQuery({ queryKey: ["categories"], queryFn: getCategories });
  // The chosen store's own pages are included, in case it is beyond the pages loaded without it.
  const storeOptions = storesOf([
    ...(storeSource.data?.pages ?? []),
    ...(listings.data?.pages ?? []),
  ]);
  const nameOf = (code: string) => text.categoryName(code, categories.data);

  return {
    filters,
    listings,
    storeOptions,
    filtered: hasFilters(filters),
    update: (changes: Partial<BrowseFilters>) =>
      setParams(searchFor({ ...filters, ...changes }), { replace: true }),
    clear: () => setParams({}, { replace: true }),
    categoryName: filters.category ? nameOf(filters.category) : null,
    storeName: storeOptions.find((store) => store.value === filters.store)?.label ?? null,
    categoryGroups: categoryGroupsOf(categories.data ?? [], nameOf, {
      food: t("household.browse.foodCategories"),
      other: t("household.browse.otherCategories"),
    }),
  };
}
