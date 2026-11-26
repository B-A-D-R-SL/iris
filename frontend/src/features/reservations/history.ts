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

export function historyUrl(page = 1): string {
  return page > 1 ? `/api/reservations/me/?page=${page}` : "/api/reservations/me/";
}

function isHistoryPage(value: unknown): value is HistoryPage {
  if (typeof value !== "object" || value === null) return false;
  const { count, results } = value as Record<string, unknown>;
  return (
    typeof count === "number" &&
    Array.isArray(results) &&
    results.every(
      (entry) =>
        typeof entry === "object" &&
        entry !== null &&
        typeof (entry as Record<string, unknown>).id === "string" &&
        typeof (entry as Record<string, unknown>).upcoming === "boolean",
    )
  );
}

export async function fetchHistoryPage(page = 1): Promise<HistoryPage> {
  const response = await fetch(historyUrl(page), {
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
    initialPageParam: 1,
    getNextPageParam: (last: HistoryPage, pages: HistoryPage[]) =>
      last.next ? pages.length + 1 : undefined,
    retry: (failures: number, error: Error) => !(error instanceof HistoryFailed) && failures < 2,
  });
}
