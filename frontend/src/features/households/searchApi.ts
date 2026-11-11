// AI contribution: 50% or more AI-generated
/** Staff household summaries; personal results stay in memory and bypass HTTP caching. */
import type { components } from "../../shared/api/generated";
import { statusTones } from "../../shared/ui/statusTones";

export type HouseholdSearchResult = components["schemas"]["HouseholdSearchResult"];
export type HouseholdSearchPage = components["schemas"]["PaginatedHouseholdSearchResultList"];

export class HouseholdSearchError extends Error {
  readonly status: number;

  constructor(status: number) {
    super(`Household search failed: ${status}`);
    this.name = "HouseholdSearchError";
    this.status = status;
  }
}

/** Ask the search endpoint to authorize this session without returning household data. */
export async function checkHouseholdSearchAccess(signal?: AbortSignal): Promise<boolean> {
  const response = await fetch("/api/staff/households/", {
    method: "HEAD",
    credentials: "same-origin",
    cache: "no-store",
    signal,
    headers: { Accept: "application/json" },
  });
  if (!response.ok) throw new HouseholdSearchError(response.status);
  return true;
}

/** Validate the identifying fields and server-provided resume permission. */
function isResult(value: unknown): value is HouseholdSearchResult {
  if (typeof value !== "object" || value === null) return false;
  const row = value as Record<string, unknown>;
  const strings = ["id", "phone", "street_number", "street_name", "unit", "city", "postal_code"];
  const nullable = ["first_name", "last_name", "email", "member_number"];
  return (
    strings.every((key) => typeof row[key] === "string") &&
    nullable.every((key) => row[key] === null || typeof row[key] === "string") &&
    typeof row.can_resume === "boolean" &&
    typeof row.status === "string" &&
    Object.hasOwn(statusTones.household, row.status) &&
    (row.channel === "walk_in" || row.channel === "online")
  );
}

/** Refuse incomplete or malformed pagination envelopes before rendering them. */
function isPage(value: unknown): value is HouseholdSearchPage {
  if (typeof value !== "object" || value === null) return false;
  const page = value as Record<string, unknown>;
  return (
    Number.isSafeInteger(page.count) &&
    Number(page.count) >= 0 &&
    Array.isArray(page.results) &&
    page.results.every(isResult) &&
    [page.next, page.previous].every((link) => link == null || typeof link === "string")
  );
}

/** Search with session authentication, cancellation and no persistent HTTP cache. */
export async function searchHouseholds(
  q: string,
  page: number,
  language: "fr" | "en",
  signal?: AbortSignal,
): Promise<HouseholdSearchPage> {
  const params = new URLSearchParams({ q, page: String(page) });
  const response = await fetch(`/api/staff/households/?${params}`, {
    credentials: "same-origin",
    cache: "no-store",
    signal,
    headers: { Accept: "application/json", "Accept-Language": language },
  });
  if (!response.ok) throw new HouseholdSearchError(response.status);
  const body: unknown = await response.json();
  if (!isPage(body)) throw new Error("Invalid household search response");
  return body;
}
