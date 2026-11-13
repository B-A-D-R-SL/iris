// AI contribution: 50% or more AI-generated
/**
 * GET /api/listings/ (US-36, T-05.36.2): the listings an approved household can
 * see, 20 a page, sorted by pickup start. The server decides what is visible;
 * the screens only show it.
 */
import {
  useInfiniteQuery,
  useQuery,
  useQueryClient,
  type InfiniteData,
  type QueryClient,
} from "@tanstack/react-query";

import type { components } from "../../shared/api/generated";

export type ListingCard = components["schemas"]["ListingCard"];
export type ListingPage = components["schemas"]["PaginatedListingCardList"];

export interface BrowseFilters {
  /** Only listings that can still be picked up today, Montreal time. */
  today: boolean;
  /** A category code, or null for every category. */
  category: string | null;
  /** A store ID, or null for every store. */
  store: string | null;
}

export const NO_FILTERS: BrowseFilters = { today: false, category: null, store: null };

/** The household's file is not approved, so it sees no listings (403). */
export const NOT_APPROVED = "household_not_approved";

/** A refused or failed browse request; `code` comes from the API's error body. */
export class BrowseFailed extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string) {
    super(`Listings unavailable: ${status} ${code}`.trim());
    this.name = "BrowseFailed";
    this.status = status;
    this.code = code;
  }
}

/** /api/listings/ with only the filters in use (the API reads a missing one as "any"). */
export function browseUrl(filters: BrowseFilters, page = 1): string {
  const params = new URLSearchParams();
  if (filters.today) params.set("today", "true");
  if (filters.category) params.set("category", filters.category);
  if (filters.store) params.set("store", filters.store);
  if (page > 1) params.set("page", String(page));
  const query = params.toString();
  return query ? `/api/listings/?${query}` : "/api/listings/";
}

function isListingPage(value: unknown): value is ListingPage {
  if (typeof value !== "object" || value === null) return false;
  const { count, results } = value as Record<string, unknown>;
  return (
    typeof count === "number" &&
    Array.isArray(results) &&
    results.every(
      (card) =>
        typeof card === "object" &&
        card !== null &&
        typeof (card as Record<string, unknown>).id === "string",
    )
  );
}

export async function fetchListingPage(filters: BrowseFilters, page = 1): Promise<ListingPage> {
  const response = await fetch(browseUrl(filters, page), {
    headers: { Accept: "application/json" },
    credentials: "same-origin",
  });
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null);
    const code =
      typeof body === "object" &&
      body !== null &&
      typeof (body as { code?: unknown }).code === "string"
        ? (body as { code: string }).code
        : "";
    throw new BrowseFailed(response.status, code);
  }
  const data: unknown = await response.json();
  if (!isListingPage(data)) throw new Error("Invalid listings API response");
  return data;
}

/**
 * A server answer (refused, or failed) is shown at once with a retry button;
 * only a lost connection is retried on its own, twice.
 */
function retryFailures(failures: number, error: Error) {
  return !(error instanceof BrowseFailed) && failures < 2;
}

/** Pages of visible listings for these filters; load the next 20 with fetchNextPage(). */
export function useListings(filters: BrowseFilters) {
  return useInfiniteQuery({
    queryKey: ["listings", filters],
    queryFn: ({ pageParam }) => fetchListingPage(filters, pageParam),
    initialPageParam: 1,
    getNextPageParam: (last: ListingPage, pages: ListingPage[]) =>
      last.next ? pages.length + 1 : undefined,
    retry: retryFailures,
  });
}

/** The card already loaded by the list, if any. */
function cachedCard(client: QueryClient, id: string): ListingCard | undefined {
  for (const [, data] of client.getQueriesData<InfiniteData<ListingPage>>({
    queryKey: ["listings"],
  })) {
    for (const page of data?.pages ?? []) {
      const card = page.results.find((result) => result.id === id);
      if (card) return card;
    }
  }
  return undefined;
}

/** Enough for every listing in the pilot; the detail endpoint (planned) will replace the search. */
const MAX_PAGES = 10;

/** Reads the unfiltered pages until the listing appears; null when it is not visible (any more). */
export async function findListingCard(id: string): Promise<ListingCard | null> {
  for (let page = 1; page <= MAX_PAGES; page += 1) {
    const result = await fetchListingPage(NO_FILTERS, page);
    const card = result.results.find((listing) => listing.id === id);
    if (card) return card;
    if (!result.next) return null;
  }
  return null;
}

/**
 * One listing for the detail screen. There is no detail endpoint yet, so it
 * reuses the card the list loaded, or finds it in the browse pages after a
 * reload or from a shared link.
 */
export function useListingCard(id: string) {
  const client = useQueryClient();
  return useQuery({
    queryKey: ["listing", id],
    queryFn: () => findListingCard(id),
    initialData: () => cachedCard(client, id),
    staleTime: 60_000,
    retry: retryFailures,
  });
}
