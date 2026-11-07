// AI contribution: 50% or more AI-generated
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { acceptInvitation, InvitationError } from "./invitations";

const ACCEPT = "/api/invitations/accept/";
const SESSION = "/api/auth/browser/v1/auth/session";
const VALUES = { token: "synthetic-invitation-token", password: " Invitation-test-431 " };

beforeEach(() => {
  document.cookie = "csrftoken=ready; Path=/";
  document.cookie = "django_language=fr; Path=/";
});

afterEach(() => {
  vi.restoreAllMocks();
  document.cookie = "csrftoken=; Max-Age=0; Path=/";
  document.cookie = "django_language=; Max-Age=0; Path=/";
});

// Size exception: this callback registers independent tests, each below 50 lines.
// One API-contract suite shares the cookie and mock cleanup above across its cases.
describe("US-04 invitation acceptance API", () => {
  it("sends only the generated request fields with language, CSRF and unchanged password", async () => {
    const fetchMock = vi.fn(async () => new Response(null, { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    const supplied = { ...VALUES, role: "admin", password_confirm: VALUES.password };
    await expect(acceptInvitation(supplied, "en")).resolves.toBeUndefined();

    expect(fetchMock).toHaveBeenCalledExactlyOnceWith(ACCEPT, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        "Accept-Language": "en",
        "X-CSRFToken": "ready",
      },
      body: JSON.stringify(VALUES),
    });
    expect(document.cookie).toContain("django_language=en");
  });

  it("gets the CSRF cookie from a signed-out 401 before submitting", async () => {
    document.cookie = "csrftoken=; Max-Age=0; Path=/";
    const fetchMock = vi.fn(async (input: RequestInfo | URL, options?: RequestInit) => {
      if (String(input) === SESSION) {
        document.cookie = "csrftoken=bootstrap-csrf; Path=/";
        return new Response(null, { status: 401 });
      }
      expect(new Headers(options?.headers).get("X-CSRFToken")).toBe("bootstrap-csrf");
      return new Response(null, { status: 200 });
    });
    vi.stubGlobal("fetch", fetchMock);

    await acceptInvitation(VALUES, "fr");

    expect(fetchMock.mock.calls.map(([url]) => String(url))).toEqual([SESSION, ACCEPT]);
    expect(fetchMock).toHaveBeenCalledWith(SESSION, { credentials: "same-origin" });
  });

  it("allows an anonymous submission when a successful bootstrap sets no CSRF cookie", async () => {
    document.cookie = "csrftoken=; Max-Age=0; Path=/";
    const fetchMock = vi.fn(async (input: RequestInfo | URL, options?: RequestInit) => {
      if (String(input) === ACCEPT) {
        expect(new Headers(options?.headers).has("X-CSRFToken")).toBe(false);
      }
      return new Response(null, { status: 200 });
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(acceptInvitation(VALUES, "fr")).resolves.toBeUndefined();
    expect(fetchMock.mock.calls.map(([url]) => String(url))).toEqual([SESSION, ACCEPT]);
  });

  it.each([
    "invitation_expired",
    "invitation_used",
    "invitation_invalid",
    "email_already_registered",
  ])("preserves the known %s machine code without copying response text", async (code) => {
    const warning = vi.spyOn(console, "warn").mockImplementation(() => {});
    const error = vi.spyOn(console, "error").mockImplementation(() => {});
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        Response.json({ code, message: `untrusted ${VALUES.token}`, fields: {} }, { status: 400 }),
      ),
    );

    await expect(acceptInvitation(VALUES, "fr")).rejects.toMatchObject({
      code,
      message: code,
      fields: {},
    });
    expect(warning).not.toHaveBeenCalled();
    expect(error).not.toHaveBeenCalled();
  });

  it("keeps valid password field messages and discards malformed field lists", async () => {
    const warning = vi.spyOn(console, "warn").mockImplementation(() => {});
    const error = vi.spyOn(console, "error").mockImplementation(() => {});
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        Response.json(
          {
            code: "validation_error",
            message: "Check the highlighted fields.",
            fields: {
              password: ["This password is too common."],
              token: "not a list",
              email: [null],
              role: [],
              store: [" "],
            },
          },
          { status: 400 },
        ),
      ),
    );

    await expect(acceptInvitation(VALUES, "en")).rejects.toMatchObject({
      code: "validation_error",
      fields: { password: ["This password is too common."] },
    });
    expect(warning).not.toHaveBeenCalled();
    expect(error).not.toHaveBeenCalled();
  });

  it.each([
    { name: "null", body: null },
    { name: "array", body: [] },
    { name: "unknown code", body: { code: "other", message: VALUES.password } },
    { name: "missing code", body: { message: "missing code" } },
  ])("uses a safe unavailable error for an unrecognized response: $name", async ({ body }) => {
    const warning = vi.spyOn(console, "warn").mockImplementation(() => {});
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => Response.json(body, { status: 400 })),
    );
    await expect(acceptInvitation(VALUES, "fr")).rejects.toMatchObject({
      code: "unavailable",
      message: "unavailable",
    });
    expect(warning).toHaveBeenCalledOnce();
    const entry = JSON.parse(String(warning.mock.calls[0]?.[0]));
    expect(entry).toEqual({
      timestamp: expect.any(String),
      level: "WARNING",
      event: "invitation_response_invalid",
    });
  });

  it("ignores non-object fields on a known error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        Response.json({ code: "validation_error", fields: "bad fields" }, { status: 400 }),
      ),
    );

    await expect(acceptInvitation(VALUES, "fr")).rejects.toMatchObject({
      code: "validation_error",
      fields: {},
    });
  });

  it.each([400, 403, 500, 503, 201])(
    "treats a non-JSON HTTP %s response as unavailable",
    async (status) => {
      const warning = vi.spyOn(console, "warn").mockImplementation(() => {});
      vi.stubGlobal(
        "fetch",
        vi.fn(
          async () =>
            new Response(`${VALUES.token} ${VALUES.password} person@example.test ${ACCEPT}`, {
              status,
            }),
        ),
      );

      await expect(acceptInvitation(VALUES, "fr")).rejects.toMatchObject({ code: "unavailable" });
      expect(warning).toHaveBeenCalledOnce();
      const entry = JSON.parse(String(warning.mock.calls[0]?.[0]));
      expect(entry).toEqual({
        timestamp: expect.any(String),
        level: "WARNING",
        event: "invitation_response_invalid",
      });
      for (const secret of [VALUES.token, VALUES.password, "person@example.test", ACCEPT]) {
        expect(String(warning.mock.calls[0]?.[0])).not.toContain(secret);
      }
    },
  );

  it("handles a network rejection without exposing the underlying message", async () => {
    const error = vi.spyOn(console, "error").mockImplementation(() => {});
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error(`network ${VALUES.token} ${VALUES.password} person@example.test ${ACCEPT}`);
      }),
    );

    await expect(acceptInvitation(VALUES, "en")).rejects.toMatchObject({
      code: "unavailable",
      message: "unavailable",
    });
    expect(error).toHaveBeenCalledOnce();
    const entry = JSON.parse(String(error.mock.calls[0]?.[0]));
    expect(entry).toEqual({
      timestamp: expect.any(String),
      level: "ERROR",
      event: "invitation_request_failed",
    });
    for (const secret of [VALUES.token, VALUES.password, "person@example.test", ACCEPT]) {
      expect(String(error.mock.calls[0]?.[0])).not.toContain(secret);
    }
  });

  it.each(["network", "status"])(
    "does not submit after a %s bootstrap failure",
    async (failure) => {
      const error = vi.spyOn(console, "error").mockImplementation(() => {});
      document.cookie = "csrftoken=; Max-Age=0; Path=/";
      const fetchMock = vi.fn(async () => {
        if (failure === "network") throw new Error("session unavailable");
        return new Response(null, { status: 503 });
      });
      vi.stubGlobal("fetch", fetchMock);

      await expect(acceptInvitation(VALUES, "fr")).rejects.toBeInstanceOf(InvitationError);
      expect(fetchMock).toHaveBeenCalledExactlyOnceWith(SESSION, { credentials: "same-origin" });
      expect(error).toHaveBeenCalledTimes(failure === "network" ? 1 : 0);
    },
  );
});
