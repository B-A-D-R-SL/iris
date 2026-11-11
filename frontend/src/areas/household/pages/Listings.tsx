// AI contribution: 50% or more AI-generated
/**
 * Browse listings (US-36, T-05.36.3), following the H1 "Find and reserve"
 * mockups: filter chips, cards sorted by pickup start, and the not-approved and
 * no-result states. Filters live in the address, so the back arrow of a detail
 * screen returns to the same list. The server decides what is visible.
 */
import { Button, Stack, Text } from "@mantine/core";
import { IconCheck, IconChevronDown } from "@tabler/icons-react";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useLocation, useSearchParams } from "react-router";

import { AppBar } from "../../../app/layouts/AppBar";
import { getCategories } from "../../../features/categories/api";
import {
  BrowseFailed,
  NOT_APPROVED,
  useListings,
  type BrowseFilters,
} from "../../../features/listings/browse";
import { EmptyState, ErrorState, LoadingState } from "../../../shared/ui";
import { filtersFrom, hasFilters, searchFor, storesOf } from "../browseFilters";
import { FilterSheet, type FilterGroup } from "../components/FilterSheet";
import { ListingCardView } from "../components/ListingCardView";
import { NotApproved } from "../components/NotApproved";
import household from "../household.module.css";
import { useListingText } from "../useListingText";
import classes from "./Listings.module.css";

export function Listings() {
  const { t } = useTranslation();
  const text = useListingText();
  const location = useLocation();
  const [params, setParams] = useSearchParams();
  const filters = filtersFrom(params);
  const filtered = hasFilters(filters);
  const [now] = useState(() => new Date());
  const [sheet, setSheet] = useState<"category" | "store" | null>(null);

  const listings = useListings(filters);
  // The store choices come from the same list without the store filter, so
  // choosing a store does not hide the others (the same query when none is chosen).
  const storeSource = useListings({ ...filters, store: null });
  const categories = useQuery({ queryKey: ["categories"], queryFn: getCategories });

  const update = (changes: Partial<BrowseFilters>) =>
    setParams(searchFor({ ...filters, ...changes }), { replace: true });

  const categoryName = filters.category
    ? text.categoryName(filters.category, categories.data)
    : null;
  // The chosen store's own pages are included, in case it is beyond the pages loaded without it.
  const storeOptions = storesOf([
    ...(storeSource.data?.pages ?? []),
    ...(listings.data?.pages ?? []),
  ]);
  const storeName = storeOptions.find((store) => store.value === filters.store)?.label ?? null;
  const categoryGroups: FilterGroup[] = [true, false]
    .map((food) => ({
      label: t(food ? "household.browse.foodCategories" : "household.browse.otherCategories"),
      options: (categories.data ?? [])
        .filter((category) => category.is_food === food)
        .map((category) => ({
          value: category.code,
          label: text.categoryName(category.code, categories.data),
        }))
        .sort((a, b) => a.label.localeCompare(b.label)),
    }))
    .filter((group) => group.options.length > 0);

  const notApproved =
    listings.error instanceof BrowseFailed && listings.error.code === NOT_APPROVED;
  const cards = listings.data?.pages.flatMap((page) => page.results) ?? [];
  const count = listings.data?.pages[0]?.count ?? 0;

  return (
    <div className={household.palette}>
      <AppBar title={t("app.householdNav.listings")} />
      {notApproved ? (
        <NotApproved />
      ) : (
        <>
          <div className={classes.filters} role="group" aria-label={t("household.browse.filters")}>
            <button
              type="button"
              className={classes.chip}
              aria-pressed={filters.today}
              onClick={() => update({ today: !filters.today })}
            >
              {filters.today && <IconCheck size={16} stroke={2} aria-hidden />}
              {t("household.browse.today")}
            </button>
            <button
              type="button"
              className={classes.chip}
              data-active={filters.category !== null || undefined}
              aria-haspopup="dialog"
              onClick={() => setSheet("category")}
            >
              {filters.category !== null && <IconCheck size={16} stroke={2} aria-hidden />}
              {categoryName ?? t("household.browse.category")}
              <IconChevronDown size={16} stroke={2} aria-hidden />
            </button>
            <button
              type="button"
              className={classes.chip}
              data-active={filters.store !== null || undefined}
              aria-haspopup="dialog"
              onClick={() => setSheet("store")}
            >
              {filters.store !== null && <IconCheck size={16} stroke={2} aria-hidden />}
              {storeName ?? t("household.browse.store")}
              <IconChevronDown size={16} stroke={2} aria-hidden />
            </button>
          </div>

          {listings.isPending ? (
            <LoadingState />
          ) : listings.isError ? (
            <ErrorState onRetry={() => void listings.refetch()} />
          ) : cards.length === 0 ? (
            filtered ? (
              <EmptyState
                title={t("household.browse.noMatchTitle")}
                description={t("household.browse.noMatchDescription")}
                action={
                  <Button variant="outline" onClick={() => setParams({}, { replace: true })}>
                    {t("household.browse.clearFilters")}
                  </Button>
                }
              />
            ) : (
              <EmptyState
                title={t("household.browse.emptyTitle")}
                description={t("household.browse.emptyDescription")}
              />
            )
          ) : (
            <Stack gap="sm" px="md" pb="lg">
              <Text size="sm" c="gray.7">
                {count === 1
                  ? t("household.browse.countOne")
                  : t("household.browse.countMany", { count })}
              </Text>
              <ul className={classes.list}>
                {cards.map((card) => (
                  <li key={card.id}>
                    <ListingCardView
                      card={card}
                      now={now}
                      linkState={{ search: location.search }}
                    />
                  </li>
                ))}
              </ul>
              {listings.hasNextPage && (
                <Button
                  variant="outline"
                  loading={listings.isFetchingNextPage}
                  onClick={() => void listings.fetchNextPage()}
                >
                  {t("household.browse.loadMore")}
                </Button>
              )}
            </Stack>
          )}

          <FilterSheet
            opened={sheet === "category"}
            onClose={() => setSheet(null)}
            title={t("household.browse.category")}
            allLabel={t("household.browse.allCategories")}
            groups={categoryGroups}
            value={filters.category}
            onChange={(category) => update({ category })}
          />
          <FilterSheet
            opened={sheet === "store"}
            onClose={() => setSheet(null)}
            title={t("household.browse.store")}
            allLabel={t("household.browse.allStores")}
            groups={storeOptions.length > 0 ? [{ options: storeOptions }] : []}
            emptyText={t("household.browse.noStores")}
            value={filters.store}
            onChange={(store) => update({ store })}
          />
        </>
      )}
    </div>
  );
}
