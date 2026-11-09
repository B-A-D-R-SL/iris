// AI contribution: 50% or more AI-generated
import { csrfToken } from "../../shared/api/csrf";

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

function isHousehold(value: unknown): value is StaffHousehold {
  if (typeof value !== "object" || value === null) return false;
  const row = value as Record<string, unknown>;
  return (
    typeof row.id === "string" &&
    typeof row.status === "string" &&
    typeof row.status_reason === "string" &&
    (row.member_number === null || typeof row.member_number === "string") &&
    (row.email === null || typeof row.email === "string") &&
    typeof row.phone === "string" &&
    (row.preferred_language === "fr" || row.preferred_language === "en") &&
    (row.expires_at === null || typeof row.expires_at === "string") &&
    Array.isArray(row.members)
  );
}

function errorBody(value: unknown): value is {
  message: string;
  fields: Record<string, string[]>;
} {
  if (typeof value !== "object" || value === null) return false;
  const body = value as Record<string, unknown>;
  return typeof body.message === "string" && typeof body.fields === "object";
}

export async function getStaffHousehold(id: string): Promise<StaffHousehold> {
  const response = await fetch(`/api/staff/households/${encodeURIComponent(id)}/`, {
    credentials: "same-origin",
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!response.ok) throw new HouseholdStatusFailed(response.status, "");
  const body: unknown = await response.json();
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
  const body: unknown = await response.json().catch(() => null);
  if (errorBody(body)) {
    throw new HouseholdStatusFailed(response.status, body.message, body.fields);
  }
  throw new HouseholdStatusFailed(response.status, "");
}
