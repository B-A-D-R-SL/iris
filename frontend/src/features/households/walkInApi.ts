// AI contribution: 50% or more AI-generated
/**
 * Walk-in drafts (US-17, T-03.17.3 endpoints): create with POST, then resume
 * with GET and save each step with PATCH. The server checks the staff role and
 * every rule again; the form only helps staff get it right the first time.
 */
import { csrfToken } from "../../shared/api/csrf";
import type { components } from "../../shared/api/generated";

export type WalkInDraft = components["schemas"]["WalkInDraftRead"];
export type WalkInInput = components["schemas"]["WalkInDraftInput"];
export type MemberRelation = components["schemas"]["MemberInputRelationEnum"];

/** A refused request: 400 has messages per field ("holder.first_name"); others only a message. */
export class WalkInFailed extends Error {
  readonly status: number;
  readonly fields: Record<string, string[]>;

  constructor(status: number, message: string, fields: Record<string, string[]> = {}) {
    super(message);
    this.name = "WalkInFailed";
    this.status = status;
    this.fields = fields;
  }
}

export const walkInQueryKey = (id: string) => ["walk-in", id] as const;

function isErrorBody(
  value: unknown,
): value is { message: string; fields: Record<string, string[]> } {
  if (typeof value !== "object" || value === null) return false;
  const { message, fields } = value as Record<string, unknown>;
  return typeof message === "string" && typeof fields === "object" && fields !== null;
}

async function request(
  path: string,
  init: { method: "GET" | "POST" | "PATCH"; body?: WalkInInput },
  language: "fr" | "en",
): Promise<WalkInDraft> {
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
  if (response.ok) return (await response.json()) as WalkInDraft;

  const error: unknown = await response.json().catch(() => null);
  if (isErrorBody(error)) throw new WalkInFailed(response.status, error.message, error.fields);
  throw new WalkInFailed(response.status, "");
}

export function getWalkIn(id: string, language: "fr" | "en"): Promise<WalkInDraft> {
  return request(`/api/staff/households/${id}/`, { method: "GET" }, language);
}

/** Creates the draft; the holder (name, date of birth, phone) is required. */
export function createWalkIn(body: WalkInInput, language: "fr" | "en"): Promise<WalkInDraft> {
  return request("/api/staff/households/", { method: "POST", body }, language);
}

export function updateWalkIn(
  id: string,
  body: WalkInInput,
  language: "fr" | "en",
): Promise<WalkInDraft> {
  return request(`/api/staff/households/${id}/`, { method: "PATCH", body }, language);
}
