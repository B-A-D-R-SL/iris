// AI contribution: 50% or more AI-generated
/** Generated stores and a fake admin store API for the US-14 screen tests. */
import { vi } from "vitest";

import type { StaffStore, StaffStorePage } from "../features/stores/adminApi";
import type { Role } from "../shared/auth/roles";
import { testUser } from "./render";

const OPEN = { open: "08:00", close: "20:00" };

export const demoStore: StaffStore = {
  id: "00000000-0000-4000-8000-0000000000aa",
  name: "Épicerie Démo du Quartier",
  street_number: "1234",
  street_name: "rue Saint-Denis",
  unit: null,
  city: "Montréal",
  postal_code: "H2X 3K2",
  phone: "+15145550110",
  email: "bonjour@epicerie-demo.example",
  opening_hours: {
    mon: OPEN,
    tue: OPEN,
    wed: OPEN,
    thu: { open: "08:00", close: "21:00" },
    fri: { open: "08:00", close: "21:00" },
    sat: { open: "09:00", close: "18:00" },
    sun: null,
    notes: null,
  },
  pickup_instructions: "Porte arrière, sonnez",
  is_badr: false,
  is_active: true,
  created_at: "2026-10-05T14:00:00Z",
  updated_at: "2026-11-10T14:00:00Z",
  open_listings: 3,
  households_to_notify: 5,
  can_change_status: true,
};

export function storePage(stores: StaffStore[] = [demoStore]): StaffStorePage {
  return {
    count: stores.length,
    next: null,
    previous: null,
    results: stores.map((store) => ({
      id: store.id,
      name: store.name,
      street_number: store.street_number,
      street_name: store.street_name,
      unit: store.unit,
      city: store.city,
      postal_code: store.postal_code,
      is_active: store.is_active,
      is_badr: store.is_badr,
      open_listings: store.open_listings,
    })),
    counts: {
      all: stores.length,
      active: stores.filter((store) => store.is_active).length,
      inactive: stores.filter((store) => !store.is_active).length,
    },
  };
}

type Handler = (body: Record<string, unknown>) => Response;

export interface StoreApiFake {
  role?: Role;
  list?: (url: URL) => Response;
  detail?: () => Response;
  patch?: Handler;
  deactivate?: Handler;
  reactivate?: Handler;
}

/** Fakes /api/me/ and the admin store endpoints; returns the fetch mock. */
export function mockStoreApi({
  role = "admin",
  list = () => Response.json(storePage()),
  detail = () => Response.json(demoStore),
  patch = (body) => Response.json({ ...demoStore, ...body }),
  deactivate = () =>
    Response.json({
      ...demoStore,
      is_active: false,
      listings_cancelled: 3,
      reservations_cancelled: 6,
    }),
  reactivate = () => Response.json({ ...demoStore, is_active: true }),
}: StoreApiFake = {}) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(input instanceof Request ? input.url : String(input), "http://iris.test");
    const method = init?.method ?? "GET";
    const body = init?.body ? (JSON.parse(init.body as string) as Record<string, unknown>) : {};
    if (url.pathname === "/api/me/") return Response.json(testUser(role));
    // Household search access (RequireHouseholdSearch) for the staff home screen.
    if (url.pathname === "/api/staff/households/" && method === "HEAD") {
      return new Response(null, {
        status: role === "intake_worker" || role === "admin" ? 200 : 403,
      });
    }
    if (url.pathname === "/api/staff/stores/") return list(url);
    if (url.pathname.endsWith("/deactivate/")) return deactivate(body);
    if (url.pathname.endsWith("/reactivate/")) return reactivate(body);
    if (url.pathname.startsWith("/api/staff/stores/")) {
      return method === "PATCH" ? patch(body) : detail();
    }
    return new Response(null, { status: 404 });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

/** The method, path and JSON body of every request sent with ``method``. */
export function sentRequests(fetchMock: ReturnType<typeof mockStoreApi>, method: string) {
  return fetchMock.mock.calls
    .filter(([, init]) => (init?.method ?? "GET") === method)
    .map(([input, init]) => ({
      path: new URL(String(input), "http://iris.test").pathname,
      body: init?.body ? (JSON.parse(init.body as string) as unknown) : null,
    }));
}
