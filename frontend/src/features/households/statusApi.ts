// AI contribution: 50% or more AI-generated
import { csrfToken } from "../../shared/api/csrf";
import { logger } from "../../shared/logger";

export type HouseholdStatus =
  | "draft"
  | "submitted"
  | "review_required"
  | "awaiting_visit"
  | "approved"
  | "renewal_needed"
  | "suspended"
  | "rejected";

export interface StaffHousehold {
  id: string;
  member_number: string | null;
  status: HouseholdStatus;
  status_reason: string;
  email: string | null;
  phone: string;
  preferred_language: "fr" | "en";
  expires_at: string | null;
  allowed_actions: Array<"suspend" | "reactivate">;
  reason_max_length: number;
  members: Array<{
    id: string;
    first_name: string;
    last_name: string;
    relation: string;
  }>;
}

export class HouseholdStatusFailed extends Error {
  readonly status: number;
  readonly fields: Record<string, string[]>;

  constructor(status: number, message: string, fields: Record<string, string[]> = {}) {
    super(message);
    this.name = "HouseholdStatusFailed";
    this.status = status;
    this.fields = fields;
  }
}

/** Validate the fields required by the staff household page. */
function isHousehold(value: unknown): value is StaffHousehold {
  if (typeof value !== "object" || value === null) return false;
  const row = value as Record<string, unknown>;
  const nullableString = (item: unknown) => item === null || typeof item === "string";
  const actions = row.allowed_actions;
  const validActions =
    Array.isArray(actions) &&
    actions.every((action) => action === "suspend" || action === "reactivate");
  return [
    typeof row.id === "string",
    typeof row.status === "string",
    typeof row.status_reason === "string",
    nullableString(row.member_number),
    nullableString(row.email),
    typeof row.phone === "string",
    row.preferred_language === "fr" || row.preferred_language === "en",
    nullableString(row.expires_at),
    validActions,
    Number.isSafeInteger(row.reason_max_length) && Number(row.reason_max_length) > 0,
    Array.isArray(row.members),
  ].every(Boolean);
}

/** Accept only the shared API error envelope with an object field map. */
function errorBody(value: unknown): value is {
  message: string;
  fields: Record<string, string[]>;
} {
  if (typeof value !== "object" || value === null) return false;
  const body = value as Record<string, unknown>;
  return (
    typeof body.message === "string" &&
    typeof body.fields === "object" &&
    body.fields !== null &&
    !Array.isArray(body.fields)
  );
}

/** Parse JSON without logging response bodies that may contain personal data. */
async function responseBody(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    logger.warning("household_status_response_invalid");
    return null;
  }
}

export async function getStaffHousehold(id: string): Promise<StaffHousehold> {
  const response = await fetch(`/api/staff/households/${encodeURIComponent(id)}/`, {
    credentials: "same-origin",
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!response.ok) throw new HouseholdStatusFailed(response.status, "");
  const body = await responseBody(response);
  if (!isHousehold(body)) throw new Error("Invalid household response");
  return body;
}

export async function changeHouseholdStatus(
  id: string,
  action: "suspend" | "reactivate",
  reason: string,
  language: "fr" | "en",
): Promise<void> {
  const headers: Record<string, string> = {
    Accept: "application/json",
    "Accept-Language": language,
    "Content-Type": "application/json",
  };
  const token = csrfToken();
  if (token) headers["X-CSRFToken"] = token;
  const response = await fetch(`/api/staff/households/${encodeURIComponent(id)}/${action}/`, {
    method: "POST",
    credentials: "same-origin",
    headers,
    body: JSON.stringify({ reason }),
  });
  if (response.ok) return;
  const body = await responseBody(response);
  if (errorBody(body)) {
    throw new HouseholdStatusFailed(response.status, body.message, body.fields);
  }
  throw new HouseholdStatusFailed(response.status, "");
}
