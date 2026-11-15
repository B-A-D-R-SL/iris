// AI contribution: 50% or more AI-generated
/**
 * Admin store management (US-14, T-02.14.2): list and search stores, read
 * one with its deactivation preview, change its fields, deactivate or
 * reactivate it with a reason. The server checks the admin role and every
 * rule again.
 */
import { csrfToken } from "../../shared/api/csrf";
import type { components } from "../../shared/api/generated";

export type StaffStore = components["schemas"]["StaffStore"];
export type StaffStoreRow = components["schemas"]["StaffStoreListItem"];
export type StaffStorePage = components["schemas"]["StaffStorePage"];
export type StoreChanges = components["schemas"]["PatchedStaffStoreUpdate"];
export type StoreDeactivated = components["schemas"]["StoreDeactivated"];
export type OpeningHours = components["schemas"]["OpeningHours"];
export type DayHours = components["schemas"]["DayHours"];
export type StoreStatusFilter = "all" | "active" | "inactive";
type Language = "fr" | "en";

/** A refused request: 400 has messages per field; 403, 404 and 409 only a message. */
export class StoreFailed extends Error {
  readonly status: number;
  readonly code: string;
  readonly fields: Record<string, string[]>;

  constructor(status: number, message: string, code = "", fields: Record<string, string[]> = {}) {
    super(message);
    this.name = "StoreFailed";
    this.status = status;
    this.code = code;
    this.fields = fields;
  }
}

export const staffStoresKey = ["staff-stores"] as const;
export const staffStoreKey = (id: string) => ["staff-store", id] as const;

function isErrorBody(
  value: unknown,
): value is { code?: string; message: string; fields: Record<string, string[]> } {
  if (typeof value !== "object" || value === null) return false;
  const { message, fields } = value as Record<string, unknown>;
  return typeof message === "string" && typeof fields === "object" && fields !== null;
}

async function request<T>(
  path: string,
  init: { method: "GET" | "POST" | "PATCH"; body?: object },
  language: Language,
): Promise<T> {
  const headers: Record<string, string> = {
    Accept: "application/json",
    "Accept-Language": language,
  };
  if (init.body) {
    headers["Content-Type"] = "application/json";
    const token = csrfToken();
    if (token) headers["X-CSRFToken"] = token;
  }
  const response = await fetch(path, {
    method: init.method,
    headers,
    body: init.body ? JSON.stringify(init.body) : undefined,
    credentials: "same-origin",
  });
  if (response.ok) return (await response.json()) as T;

  const error: unknown = await response.json().catch(() => null);
  if (isErrorBody(error)) {
    throw new StoreFailed(
      response.status,
      error.message,
      typeof error.code === "string" ? error.code : "",
      error.fields,
    );
  }
  throw new StoreFailed(response.status, "");
}

const storeUrl = (id: string) => `/api/staff/stores/${encodeURIComponent(id)}/`;

export function listStores(
  filters: { q: string; status: StoreStatusFilter; page: number },
  language: Language,
): Promise<StaffStorePage> {
  const query = new URLSearchParams({ page: String(filters.page) });
  if (filters.q.trim()) query.set("q", filters.q.trim());
  if (filters.status !== "all") query.set("status", filters.status);
  return request<StaffStorePage>(`/api/staff/stores/?${query}`, { method: "GET" }, language);
}

export function getStore(id: string, language: Language): Promise<StaffStore> {
  return request<StaffStore>(storeUrl(id), { method: "GET" }, language);
}

export function updateStore(
  id: string,
  changes: Partial<StoreChanges>,
  language: Language,
): Promise<StaffStore> {
  return request<StaffStore>(storeUrl(id), { method: "PATCH", body: changes }, language);
}

export function deactivateStore(
  id: string,
  reason: string,
  language: Language,
): Promise<StoreDeactivated> {
  return request<StoreDeactivated>(
    `${storeUrl(id)}deactivate/`,
    { method: "POST", body: { reason } },
    language,
  );
}

export function reactivateStore(
  id: string,
  reason: string,
  language: Language,
): Promise<StaffStore> {
  return request<StaffStore>(
    `${storeUrl(id)}reactivate/`,
    { method: "POST", body: { reason } },
    language,
  );
}
