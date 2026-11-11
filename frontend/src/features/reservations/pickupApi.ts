// AI contribution: 50% or more AI-generated
/**
 * Store pickup lookup and confirm (US-44, T-06.44.3). Thin client over
 * POST /api/store/pickups/lookup/ and POST /api/store/pickups/{id}/confirm/.
 */
import { csrfToken } from "../../shared/api/csrf";
import type { components } from "../../shared/api/generated";

export type Pickup = components["schemas"]["Pickup"];
export type PickupError = components["schemas"]["PickupError"];

/** A refused lookup or confirm: the `code` drives the scan screen copy. */
export class PickupFailed extends Error {
  readonly status: number;
  readonly code: string;
  readonly picked_up_at: string | null;

  constructor(status: number, error: PickupError) {
    super(error.message);
    this.name = "PickupFailed";
    this.status = status;
    this.code = error.code;
    this.picked_up_at = error.picked_up_at ?? null;
  }
}

function isPickupError(value: unknown): value is PickupError {
  if (typeof value !== "object" || value === null) return false;
  const { code, message, fields } = value as Record<string, unknown>;
  return (
    typeof code === "string" &&
    typeof message === "string" &&
    typeof fields === "object" &&
    fields !== null
  );
}

async function postPickup(path: string, language: "fr" | "en", body?: object): Promise<Pickup> {
  const headers: Record<string, string> = {
    Accept: "application/json",
    "Accept-Language": language,
    "Content-Type": "application/json",
  };
  const token = csrfToken();
  if (token) headers["X-CSRFToken"] = token;

  const response = await fetch(path, {
    method: "POST",
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
    credentials: "same-origin",
  });
  if (response.status === 200) return (await response.json()) as Pickup;

  const error: unknown = await response.json().catch(() => null);
  if (isPickupError(error)) throw new PickupFailed(response.status, error);
  throw new PickupFailed(response.status, {
    code: "unavailable",
    message: "",
    fields: {},
  });
}

/** Find who and what for a typed or scanned code; changes nothing. */
export function lookupPickup(code: string, language: "fr" | "en"): Promise<Pickup> {
  return postPickup("/api/store/pickups/lookup/", language, { code });
}

/** One tap: mark the reservation picked up with who and when. */
export function confirmPickup(id: string, language: "fr" | "en"): Promise<Pickup> {
  return postPickup(`/api/store/pickups/${id}/confirm/`, language);
}
