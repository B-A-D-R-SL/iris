// AI contribution: 50% or more AI-generated
/**
 * Admin category management (US-35, T-05.35.2): list every category, add one,
 * and change one by its code (rename, food, default value, active). There is no
 * delete. The server checks the admin role and every rule again.
 */
import { csrfToken } from "../../shared/api/csrf";
import type { components } from "../../shared/api/generated";

export type StaffCategory = components["schemas"]["StaffCategory"];
export type CategoryChanges = components["schemas"]["PatchedStaffCategory"];

/** A refused request: 400 has messages per field; 403, 404 and 503 only a message. */
export class CategoryFailed extends Error {
  readonly status: number;
  readonly fields: Record<string, string[]>;

  constructor(status: number, message: string, fields: Record<string, string[]> = {}) {
    super(message);
    this.name = "CategoryFailed";
    this.status = status;
    this.fields = fields;
  }
}

/** Every category for admins; the public, active-only list keeps its own key. */
export const staffCategoriesKey = ["staff-categories"] as const;

function isErrorBody(
  value: unknown,
): value is { message: string; fields: Record<string, string[]> } {
  if (typeof value !== "object" || value === null) return false;
  const { message, fields } = value as Record<string, unknown>;
  return typeof message === "string" && typeof fields === "object" && fields !== null;
}

async function request<T>(
  path: string,
  init: { method: "GET" | "POST" | "PATCH"; body?: object },
  language: "fr" | "en",
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
  if (isErrorBody(error)) throw new CategoryFailed(response.status, error.message, error.fields);
  throw new CategoryFailed(response.status, "");
}

export function listStaffCategories(language: "fr" | "en"): Promise<StaffCategory[]> {
  return request<StaffCategory[]>("/api/staff/categories/", { method: "GET" }, language);
}

export function createCategory(
  category: StaffCategory,
  language: "fr" | "en",
): Promise<StaffCategory> {
  return request<StaffCategory>(
    "/api/staff/categories/",
    { method: "POST", body: category },
    language,
  );
}

export function updateCategory(
  code: string,
  changes: CategoryChanges,
  language: "fr" | "en",
): Promise<StaffCategory> {
  return request<StaffCategory>(
    `/api/staff/categories/${encodeURIComponent(code)}/`,
    { method: "PATCH", body: changes },
    language,
  );
}
