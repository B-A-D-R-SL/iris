// AI contribution: 50% or more AI-generated
/**
 * GET /api/reservations/me/ (US-48): the signed-in household's reservations,
 * upcoming ones first, then the past ones, 20 a page. The server decides which
 * are upcoming and whether a pickup code is sent; the screen only shows them.
 */
import { useInfiniteQuery } from "@tanstack/react-query";

import type { components } from "../../shared/api/generated";

export type HistoryEntry = components["schemas"]["HistoryEntry"];
export type HistoryPage = components["schemas"]["PaginatedHistoryEntryList"];

/** The server answered, but not with a page (for example 401 or 500). */
export class HistoryFailed extends Error {
  readonly status: number;

  constructor(status: number) {
    super(`Reservations unavailable: ${status}`);
    this.name = "HistoryFailed";
    this.status = status;
  }
}

/** Which page to read, and the time page 1 was read (from the API's next link). */
export interface HistoryPageParam {
  page: number;
  asOf?: string;
}

export const FIRST_PAGE: HistoryPageParam = { page: 1 };

export function historyUrl({ page, asOf }: HistoryPageParam = FIRST_PAGE): string {
  const params = new URLSearchParams();
  if (page > 1) params.set("page", String(page));
  if (asOf) params.set("as_of", asOf);
  const query = params.toString();
  return query ? `/api/reservations/me/?${query}` : "/api/reservations/me/";
}

/**
 * The next page and its `as_of` from the API's `next` link, so every page is
 * ordered as at page 1's time and no row repeats or goes missing.
 */
export function nextPageParam(next: string | null | undefined): HistoryPageParam | undefined {
  if (!next) return undefined;
  const params = new URL(next, window.location.origin).searchParams;
  const page = Number(params.get("page"));
  if (!Number.isInteger(page) || page < 2) return undefined;
  const asOf = params.get("as_of");
  return asOf ? { page, asOf } : { page };
}

type Fields = Record<string, unknown>;

const isRecord = (value: unknown): value is Fields => typeof value === "object" && value !== null;
const areStrings = (record: Fields, names: readonly string[]) =>
  names.every((name) => typeof record[name] === "string");
const isTextOrNull = (value: unknown) => value === null || typeof value === "string";

// What the reservation card reads (ReservationCard, useReservationText).
const ENTRY_TEXT = ["id", "status", "title", "unit", "pickup_start", "pickup_end"] as const;
const STORE_TEXT = ["name", "street_number", "street_name", "city", "postal_code"] as const;

function isStore(value: unknown): boolean {
  return isRecord(value) && areStrings(value, STORE_TEXT) && isTextOrNull(value.unit);
}

function isHistoryEntry(value: unknown): value is HistoryEntry {
  return (
    isRecord(value) &&
    areStrings(value, ENTRY_TEXT) &&
    typeof value.upcoming === "boolean" &&
    typeof value.quantity === "number" &&
    isTextOrNull(value.picked_up_at) &&
    isTextOrNull(value.pickup_code) &&
    isStore(value.store)
  );
}

function isHistoryPage(value: unknown): value is HistoryPage {
  return (
    isRecord(value) &&
    typeof value.count === "number" &&
    Array.isArray(value.results) &&
    value.results.every(isHistoryEntry)
  );
}

export async function fetchHistoryPage(param: HistoryPageParam = FIRST_PAGE): Promise<HistoryPage> {
  const response = await fetch(historyUrl(param), {
    headers: { Accept: "application/json" },
    credentials: "same-origin",
  });
  if (!response.ok) throw new HistoryFailed(response.status);
  const data: unknown = await response.json();
  if (!isHistoryPage(data)) throw new Error("Invalid reservations API response");
  return data;
}

/**
 * Pages of the household's reservations; load the next 20 with fetchNextPage().
 * A server answer is shown at once; only a lost connection is retried, twice.
 */
export function useReservationHistory() {
  return useInfiniteQuery({
    queryKey: ["reservations", "mine"],
    queryFn: ({ pageParam }) => fetchHistoryPage(pageParam),
    initialPageParam: FIRST_PAGE,
    getNextPageParam: (last: HistoryPage) => nextPageParam(last.next),
    retry: (failures: number, error: Error) => !(error instanceof HistoryFailed) && failures < 2,
  });
}
