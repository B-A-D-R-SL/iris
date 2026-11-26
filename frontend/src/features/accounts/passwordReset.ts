// AI contribution: 50% or more AI-generated
import { sendAuthRequest } from "../../shared/auth/api";
import { logger } from "../../shared/logger";

export type PasswordResetErrorCode =
  "invalidEmail" | "invalidLink" | "weakPassword" | "rateLimited" | "unavailable";

export class PasswordResetError extends Error {
  readonly code: PasswordResetErrorCode;

  constructor(code: PasswordResetErrorCode) {
    super(code);
    this.code = code;
    this.name = "PasswordResetError";
  }
}

const PASSWORD_POLICY_CODES = new Set([
  "password_too_short",
  "password_too_common",
  "password_entirely_numeric",
  "password_too_similar",
]);

function record(value: unknown): Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function validationError(errors: unknown, requesting: boolean): PasswordResetErrorCode | null {
  if (!Array.isArray(errors)) return null;
  const fields = errors.map(record);
  if (requesting) {
    return fields.some(({ param, code }) => param === "email" && typeof code === "string")
      ? "invalidEmail"
      : null;
  }
  if (fields.some(({ param, code }) => param === "key" && code === "invalid_password_reset")) {
    return "invalidLink";
  }
  if (
    fields.some(
      ({ param, code }) =>
        param === "password" && typeof code === "string" && PASSWORD_POLICY_CODES.has(code),
    )
  ) {
    return "weakPassword";
  }
  return null;
}

/** allauth reports the browser's resulting session after a successful reset. */
function resetSucceeded(status: number, body: Record<string, unknown>): boolean {
  const data = record(body.data);
  const authenticated = record(body.meta).is_authenticated;
  if (status === 200) {
    return (
      authenticated === true &&
      Object.keys(record(data.user)).length > 0 &&
      Array.isArray(data.methods)
    );
  }
  return (
    status === 401 &&
    authenticated === false &&
    Array.isArray(data.flows) &&
    data.flows.some((flow) => record(flow).id === "login")
  );
}

async function readResponse(response: Response, requesting: boolean): Promise<void> {
  if (response.status === 429) throw new PasswordResetError("rateLimited");
  const body = record(await response.json());
  if (body.status === response.status) {
    if (response.status === 400) {
      const code = validationError(body.errors, requesting);
      if (code) throw new PasswordResetError(code);
    }
    if (
      body.errors === undefined &&
      (requesting ? response.status === 200 : resetSucceeded(response.status, body))
    ) {
      return;
    }
  }
  throw new PasswordResetError("unavailable");
}

async function postReset(
  operation: "request" | "reset",
  payload: object,
  language: string,
): Promise<void> {
  const locale = language === "en" ? "en" : "fr";
  document.cookie = `django_language=${locale}; Path=/; SameSite=Lax`;
  let response: Response;
  try {
    response = await sendAuthRequest("POST", `/password/${operation}`, locale, payload);
  } catch {
    logger.error("password_reset_request_failed");
    throw new PasswordResetError("unavailable");
  }
  try {
    await readResponse(response, operation === "request");
  } catch (error) {
    if (error instanceof PasswordResetError && error.code !== "unavailable") throw error;
    logger.warning("password_reset_response_invalid");
    throw new PasswordResetError("unavailable");
  }
}

export async function requestPasswordReset(email: string, language: string): Promise<void> {
  await postReset("request", { email }, language);
}

export async function resetPassword(
  key: string,
  password: string,
  language: string,
): Promise<void> {
  await postReset("reset", { key, password }, language);
}
