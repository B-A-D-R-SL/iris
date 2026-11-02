// AI contribution: 50% or more AI-generated
import type { components } from "../../../shared/api/generated";
import { csrfToken } from "../../../shared/api/csrf";

export type Application = components["schemas"]["PartnerApplication"];
export type ApplicationValues = Omit<
  Application,
  "business_type" | "expected_frequency" | "neq" | "website" | "unit" | "contact_role" | "message"
> & {
  business_type: string;
  expected_frequency: string;
  neq: string;
  website: string;
  unit: string;
  contact_role: string;
  message: string;
};

export const initialValues: ApplicationValues = {
  business_name: "",
  business_type: "",
  neq: "",
  website: "",
  street_number: "",
  street_name: "",
  unit: "",
  city: "Montréal",
  postal_code: "",
  contact_first_name: "",
  contact_last_name: "",
  contact_role: "",
  contact_email: "",
  contact_phone: "",
  goods_categories: [],
  expected_frequency: "",
  opening_hours: "",
  message: "",
  consent_contact: false,
};

export class ApplicationError extends Error {
  readonly status: number;
  readonly fields: Record<string, string[]>;

  constructor(status: number, message: string, fields: Record<string, string[]> = {}) {
    super(message);
    this.status = status;
    this.fields = fields;
  }
}

export async function submitApplication(
  values: ApplicationValues,
  language: string,
): Promise<void> {
  const headers: Record<string, string> = {
    Accept: "application/json",
    "Content-Type": "application/json",
    "Accept-Language": language,
  };
  let token = csrfToken();
  if (!token) {
    // Session-authenticated users need CSRF even though this endpoint is public.
    // The signed-out response may be 401; it still sets the CSRF cookie.
    await fetch("/api/auth/browser/v1/auth/session", { credentials: "same-origin" });
    token = csrfToken();
  }
  if (token) headers["X-CSRFToken"] = token;
  const response = await fetch("/api/partner-applications/", {
    method: "POST",
    credentials: "same-origin",
    headers,
    body: JSON.stringify(values),
  });
  if (response.status === 201) return;
  const data: unknown = await response.json().catch(() => null);
  if (data && typeof data === "object" && "message" in data && typeof data.message === "string") {
    const fields =
      "fields" in data && data.fields && typeof data.fields === "object"
        ? (data.fields as Record<string, string[]>)
        : {};
    throw new ApplicationError(response.status, data.message, fields);
  }
  throw new ApplicationError(response.status, "");
}
