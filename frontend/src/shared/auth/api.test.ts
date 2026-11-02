// AI contribution: 50% or more AI-generated
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AuthError, loginWithCode, loginWithPassword, logout } from "./api";

const authBase = "/api/auth/browser/v1/auth";

beforeEach(() => {
  document.cookie = "csrftoken=; Max-Age=0";
});

describe("allauth browser session", () => {
  it("gets a CSRF cookie before sign-in and sends it with the password", async () => {
    const fetchMock = vi.fn(async (url: string, options?: RequestInit) => {
      if (url === `${authBase}/session`) {
        document.cookie = "csrftoken=test-csrf; path=/";
        return new Response(null, { status: 401 });
      }
      expect(options).toMatchObject({
        method: "POST",
        credentials: "same-origin",
        body: JSON.stringify({ email: "user@example.test", password: "secret" }),
      });
      expect(options?.headers).toMatchObject({
        "X-CSRFToken": "test-csrf",
        "Accept-Language": "fr",
      });
      return Response.json({});
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(loginWithPassword("user@example.test", "secret", "fr")).resolves.toBe(
      "authenticated",
    );
    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
      `${authBase}/session`,
      `${authBase}/login`,
    ]);
  });

  it("uses one generic error for invalid or unknown credentials", async () => {
    document.cookie = "csrftoken=ready; path=/";
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => Response.json({ errors: [{ code: "invalid_password" }] }, { status: 401 })),
    );
    await expect(loginWithPassword("person@example.test", "bad", "en")).rejects.toMatchObject({
      code: "invalid_credentials",
    });
  });

  it("recognizes lockout and requests a code only for a real MFA challenge", async () => {
    document.cookie = "csrftoken=ready; path=/";
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        Response.json({ errors: [{ code: "too_many_login_attempts" }] }, { status: 400 }),
      )
      .mockResolvedValueOnce(
        Response.json({ data: { flows: [{ id: "mfa_authenticate" }] } }, { status: 401 }),
      );
    vi.stubGlobal("fetch", fetchMock);
    await expect(loginWithPassword("person@example.test", "bad", "fr")).rejects.toMatchObject({
      code: "locked",
    });
    await expect(loginWithPassword("person@example.test", "correct", "fr")).resolves.toBe(
      "mfa_required",
    );
  });

  it("sends the six digit code to allauth and handles an invalid code", async () => {
    document.cookie = "csrftoken=ready; path=/";
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(Response.json({ errors: [] }, { status: 400 }))
      .mockResolvedValueOnce(Response.json({}));
    vi.stubGlobal("fetch", fetchMock);
    await expect(loginWithCode("123456", "fr")).rejects.toMatchObject({ code: "invalid_code" });
    await expect(loginWithCode("654321", "en")).resolves.toBeUndefined();
    expect(fetchMock).toHaveBeenCalledWith(
      `${authBase}/2fa/authenticate`,
      expect.objectContaining({ method: "POST", body: JSON.stringify({ code: "654321" }) }),
    );
  });

  it("accepts allauth's signed-out 401 and rejects a failed logout", async () => {
    document.cookie = "csrftoken=ready; path=/";
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(null, { status: 401 }))
      .mockResolvedValueOnce(new Response(null, { status: 403 }));
    vi.stubGlobal("fetch", fetchMock);
    await expect(logout("fr")).resolves.toBeUndefined();
    await expect(logout("fr")).rejects.toBeInstanceOf(AuthError);
    expect(fetchMock).toHaveBeenCalledWith(
      `${authBase}/session`,
      expect.objectContaining({ method: "DELETE", credentials: "same-origin" }),
    );
  });
});
