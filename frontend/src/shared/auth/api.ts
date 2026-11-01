// AI contribution: 50% or more AI-generated
/** Browser session requests use Django's CSRF cookie, never a stored auth token. */
const AUTH = "/api/auth/browser/v1/auth";

export type AuthErrorCode =
  "invalid_credentials" | "locked" | "invalid_code" | "unavailable" | "profile_unavailable";

export class AuthError extends Error {
  readonly code: AuthErrorCode;

  constructor(code: AuthErrorCode) {
    super(code);
    this.code = code;
    this.name = "AuthError";
  }
}

type AuthBody = {
  errors?: { code?: string }[];
  data?: { flows?: { id?: string }[] };
};

function csrfCookie(): string | null {
  const entry = document.cookie
    .split(";")
    .map((part) => part.trim())
    .find((part) => part.startsWith("csrftoken="));
  return entry ? decodeURIComponent(entry.slice("csrftoken=".length)) : null;
}

async function csrfToken(): Promise<string> {
  let token = csrfCookie();
  if (!token) {
    // A signed-out session returns 401 but still sets the CSRF cookie.
    try {
      await fetch(`${AUTH}/session`, { credentials: "same-origin" });
    } catch {
      throw new AuthError("unavailable");
    }
    token = csrfCookie();
  }
  if (!token) throw new AuthError("unavailable");
  return token;
}

async function send(method: "POST" | "DELETE", path: string, language: string, body?: object) {
  const token = await csrfToken();
  try {
    return await fetch(`${AUTH}${path}`, {
      method,
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
        "Accept-Language": language,
        "Content-Type": "application/json",
        "X-CSRFToken": token,
      },
      ...(body ? { body: JSON.stringify(body) } : {}),
    });
  } catch {
    throw new AuthError("unavailable");
  }
}

async function readBody(response: Response): Promise<AuthBody> {
  try {
    const body: unknown = await response.json();
    return typeof body === "object" && body !== null ? (body as AuthBody) : {};
  } catch {
    return {};
  }
}

/** A 401 with mfa_authenticate is a pending second step, not a signed-in user. */
export async function loginWithPassword(
  email: string,
  password: string,
  language: string,
): Promise<"authenticated" | "mfa_required"> {
  const response = await send("POST", "/login", language, { email, password });
  // A live browser session can remain after a failed /api/me/ lookup.
  if (response.ok || response.status === 409) return "authenticated";
  const body = await readBody(response);
  if (response.status === 401 && body.data?.flows?.some((flow) => flow.id === "mfa_authenticate")) {
    return "mfa_required";
  }
  if (body.errors?.some((error) => error.code === "too_many_login_attempts")) {
    throw new AuthError("locked");
  }
  if (response.status === 400 || response.status === 401) {
    throw new AuthError("invalid_credentials");
  }
  throw new AuthError("unavailable");
}

export async function loginWithCode(code: string, language: string): Promise<void> {
  const response = await send("POST", "/2fa/authenticate", language, { code });
  if (response.ok) return;
  if (response.status === 400 || response.status === 401) throw new AuthError("invalid_code");
  throw new AuthError("unavailable");
}

export async function logout(language: string): Promise<void> {
  const response = await send("DELETE", "/session", language);
  // allauth returns the resulting unauthenticated session as HTTP 401.
  if (response.status !== 401 && !response.ok) throw new AuthError("unavailable");
}
