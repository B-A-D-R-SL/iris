// AI contribution: 50% or more AI-generated
/**
 * POST /api/reservations/ (US-41). The server decides everything that matters:
 * who may reserve, the limits, and whether units are left. This client only
 * sends the request and reports the server's answer.
 */
import { csrfToken } from "../../shared/api/csrf";
import type { components } from "../../shared/api/generated";

export type Reservation = components["schemas"]["Reservation"];
type ApiError = components["schemas"]["BrowseError"];

/** A refused reservation: the server's `code` picks the message to show. */
export class ReserveFailed extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "ReserveFailed";
    this.status = status;
    this.code = code;
  }
}

function isApiError(value: unknown): value is ApiError {
  if (typeof value !== "object" || value === null) return false;
  const { code, message } = value as Record<string, unknown>;
  return typeof code === "string" && typeof message === "string";
}

/** Reserves `quantity` units of a listing for the signed-in household. */
export async function reserve(
  listingId: string,
  quantity: number,
  language: "fr" | "en",
): Promise<Reservation> {
  const headers: Record<string, string> = {
    Accept: "application/json",
    "Accept-Language": language,
    "Content-Type": "application/json",
  };
  const token = csrfToken();
  if (token) headers["X-CSRFToken"] = token;
  const response = await fetch("/api/reservations/", {
    method: "POST",
    headers,
    body: JSON.stringify({ listing_id: listingId, quantity }),
    credentials: "same-origin",
  });
  if (response.status === 201) return (await response.json()) as Reservation;

  const error: unknown = await response.json().catch(() => null);
  if (isApiError(error)) throw new ReserveFailed(response.status, error.code, error.message);
  throw new ReserveFailed(response.status, "request_refused", "");
}
