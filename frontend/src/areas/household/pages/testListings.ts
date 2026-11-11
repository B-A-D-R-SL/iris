// AI contribution: 50% or more AI-generated
/** Fake API answers for the browse and detail screen tests (synthetic data only). */
import { vi } from "vitest";

import type { ListingCard } from "../../../features/listings/browse";
import { testUser } from "../../../test/render";

export const CATEGORIES = [
  {
    code: "bakery",
    name_fr: "Boulangerie",
    name_en: "Bakery",
    is_food: true,
    default_value_cents: 400,
  },
  {
    code: "hygiene",
    name_fr: "Hygiène personnelle",
    name_en: "Personal hygiene",
    is_food: false,
    default_value_cents: 300,
  },
];

export const CORNER_BAKERY = {
  id: "00000000-0000-4000-8000-0000000000b1",
  name: "Boulangerie du Coin",
  street_number: "1234",
  street_name: "rue Exemple",
  unit: null,
  city: "Montréal",
  postal_code: "H2X 1Y4",
};

export const NEIGHBOURHOOD_GROCERY = {
  ...CORNER_BAKERY,
  id: "00000000-0000-4000-8000-0000000000b2",
  name: "Épicerie du Quartier",
};

/** Today 16 h – 18 h in Montreal, 7 items left, best before tomorrow. */
export function card(overrides: Partial<ListingCard> = {}): ListingCard {
  return {
    id: "00000000-0000-4000-8000-000000000101",
    title: "Pains de la veille",
    category: "bakery",
    store: CORNER_BAKERY,
    pickup_start: "2026-11-12T21:00:00Z",
    pickup_end: "2026-11-12T23:00:00Z",
    units_left: 7,
    unit: "item",
    best_before: "2026-11-13",
    photo_url: null,
    ...overrides,
  };
}

export function page(
  cards: ListingCard[],
  { next = null as string | null, count = cards.length } = {},
) {
  return Response.json({ count, next, previous: null, results: cards });
}

/** Fakes /api/me/ (an approved household's user), /api/categories/ and /api/listings/. */
export function mockBrowseApi(listings: (url: URL) => Response) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const href = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
    const url = new URL(href, "http://localhost");
    if (url.pathname === "/api/me/") return Response.json(testUser("beneficiary"));
    if (url.pathname === "/api/categories/") return Response.json(CATEGORIES);
    if (url.pathname === "/api/listings/") return listings(url);
    return new Response(null, { status: 404 });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

/** The /api/listings/ addresses requested so far, in order. */
export function listingRequests(fetchMock: ReturnType<typeof mockBrowseApi>) {
  return fetchMock.mock.calls
    .map(([input]) => String(input))
    .filter((url) => url.startsWith("/api/listings/"));
}

export const notApproved = () =>
  Response.json(
    {
      code: "household_not_approved",
      message: "Seuls les foyers approuvés peuvent voir les offres.",
      fields: {},
    },
    { status: 403 },
  );
