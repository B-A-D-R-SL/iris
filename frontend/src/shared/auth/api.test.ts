// AI contribution: 50% or more AI-generated
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AuthError, loginWithPassword, logout } from "./api";

const authBase = "/api/auth/browser/v1/auth";

beforeEach(() => {
  document.cookie = "csrftoken=; Max-Age=0";
});

describe("allauth password sign-in", () => {
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

    await expect(loginWithPassword("user@example.test", "secret", "fr")).resolves.toBeUndefined();
    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
      `${authBase}/session`,
      `${authBase}/login`,
    ]);
  });
});

describe("allauth sign-in errors and challenges", () => {
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

  it("handles allauth's native 429 without requiring the DRF error envelope", async () => {
    document.cookie = "csrftoken=ready; path=/";
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => Response.json({ status: 429 }, { status: 429 })),
    );

    await expect(loginWithPassword("person@example.test", "secret", "en")).rejects.toMatchObject({
      code: "unavailable",
    });
  });

  it("recognizes failed-credential lockouts", async () => {
    document.cookie = "csrftoken=ready; path=/";
    const fetchMock = vi.fn(async () =>
      Response.json({ errors: [{ code: "too_many_login_attempts" }] }, { status: 400 }),
    );
    vi.stubGlobal("fetch", fetchMock);
    await expect(loginWithPassword("person@example.test", "bad", "fr")).rejects.toMatchObject({
      code: "locked",
    });
  });

  it("refuses an unexpected MFA challenge until US-09 supplies the server flow", async () => {
    document.cookie = "csrftoken=ready; path=/";
    const fetchMock = vi.fn(async (url: string) => {
      expect(url).toBe(`${authBase}/login`);
      return Response.json({ data: { flows: [{ id: "mfa_authenticate" }] } }, { status: 401 });
    });
    vi.stubGlobal("fetch", fetchMock);
    await expect(loginWithPassword("person@example.test", "secret", "fr")).rejects.toMatchObject({
      code: "unavailable",
    });
    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([`${authBase}/login`]);
  });
});

describe("allauth sign-out", () => {
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
