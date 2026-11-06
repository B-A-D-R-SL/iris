// AI contribution: 50% or more AI-generated
/** Token-authorized account setup; acceptance never changes the browser session. */
import type { components } from "../../shared/api/generated";
import { csrfToken } from "../../shared/api/csrf";

type InvitationValues = components["schemas"]["AcceptInvitation"];
const ACCEPT = "/api/invitations/accept/";
const SESSION = "/api/auth/browser/v1/auth/session";
const ERROR_CODES = [
  "invitation_expired",
  "invitation_used",
  "invitation_invalid",
  "email_already_registered",
  "validation_error",
] as const;

export type InvitationErrorCode = (typeof ERROR_CODES)[number] | "unavailable";

export class InvitationError extends Error {
  readonly code: InvitationErrorCode;
  readonly fields: Record<string, string[]>;

  constructor(code: InvitationErrorCode, fields: Record<string, string[]> = {}) {
    super(code);
    this.name = "InvitationError";
    this.code = code;
    this.fields = fields;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** Accept only field lists that can safely become ordinary React text. */
function fieldMessages(value: unknown): Record<string, string[]> {
  if (!isRecord(value)) return {};
  return Object.fromEntries(
    Object.entries(value).filter(
      ([, messages]) =>
        Array.isArray(messages) &&
        messages.length > 0 &&
        messages.every((message) => typeof message === "string" && message.trim().length > 0),
    ),
  ) as Record<string, string[]>;
}

/** Keep only the known machine code; never expose raw response or network text. */
async function responseError(response: Response): Promise<InvitationError> {
  const data: unknown = await response.json().catch(() => null);
  if (
    response.status !== 400 ||
    !isRecord(data) ||
    typeof data.code !== "string" ||
    !(ERROR_CODES as readonly string[]).includes(data.code)
  ) {
    return new InvitationError("unavailable");
  }
  return new InvitationError(data.code as InvitationErrorCode, fieldMessages(data.fields));
}

/** Follow the public-form CSRF bootstrap while matching Django's locale cookie. */
async function invitationHeaders(language: string): Promise<Record<string, string>> {
  const locale = language === "en" ? "en" : "fr";
  const headers: Record<string, string> = {
    Accept: "application/json",
    "Content-Type": "application/json",
    "Accept-Language": locale,
  };
  let csrf = csrfToken();
  if (!csrf) {
    const session = await fetch(SESSION, { credentials: "same-origin" });
    if (!session.ok && session.status !== 401) throw new InvitationError("unavailable");
    csrf = csrfToken();
  }
  if (csrf) headers["X-CSRFToken"] = csrf;
  document.cookie = `django_language=${locale}; Path=/; SameSite=Lax`;
  return headers;
}

/** Submit only the generated request fields, preserving the password exactly. */
export async function acceptInvitation(values: InvitationValues, language: string): Promise<void> {
  try {
    const headers = await invitationHeaders(language);
    const response = await fetch(ACCEPT, {
      method: "POST",
      credentials: "same-origin",
      headers,
      body: JSON.stringify({ token: values.token, password: values.password }),
    });
    if (response.status === 200) return;
    throw await responseError(response);
  } catch (error) {
    if (error instanceof InvitationError) throw error;
    throw new InvitationError("unavailable");
  }
}
