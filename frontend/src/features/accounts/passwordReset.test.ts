// AI contribution: 50% or more AI-generated
import { beforeEach, expect, it, vi } from "vitest";

import { requestPasswordReset, resetPassword } from "./passwordReset";

const AUTH = "/api/auth/browser/v1/auth";
const email = "reset-test@example.invalid";
const key = "test-user-test-key";
const password = "  new-example-password  ";

function respond(body: unknown, status: number) {
  const fetchMock = vi.fn(async () => Response.json(body, { status }));
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

beforeEach(() => {
  document.cookie = "csrftoken=reset-test; Path=/";
});

it("posts a reset request with the selected language and CSRF token", async () => {
  const fetchMock = respond({ status: 200 }, 200);
  await expect(requestPasswordReset(email, "en")).resolves.toBeUndefined();
  expect(fetchMock).toHaveBeenCalledWith(`${AUTH}/password/request`, {
    method: "POST",
    credentials: "same-origin",
    headers: {
      Accept: "application/json",
      "Accept-Language": "en",
      "Content-Type": "application/json",
      "X-CSRFToken": "reset-test",
    },
    body: JSON.stringify({ email }),
  });
});

it("obtains a CSRF cookie from the browser session before posting", async () => {
  document.cookie = "csrftoken=; Max-Age=0; Path=/";
  const fetchMock = respond({ status: 200 }, 200).mockImplementationOnce(async () => {
    document.cookie = "csrftoken=refreshed-csrf; Path=/";
    return new Response(null, { status: 401 });
  });
  await requestPasswordReset(email, "fr");
  expect(fetchMock).toHaveBeenNthCalledWith(1, `${AUTH}/session`, { credentials: "same-origin" });
  expect(fetchMock).toHaveBeenNthCalledWith(
    2,
    `${AUTH}/password/request`,
    expect.objectContaining({
      headers: expect.objectContaining({ "X-CSRFToken": "refreshed-csrf" }),
    }),
  );
});

it("recognizes signed-out reset success and preserves the password exactly", async () => {
  const fetchMock = respond(
    { status: 401, data: { flows: [{ id: "login" }] }, meta: { is_authenticated: false } },
    401,
  );
  await expect(resetPassword(key, password, "fr")).resolves.toBeUndefined();
  expect(fetchMock).toHaveBeenCalledWith(
    `${AUTH}/password/reset`,
    expect.objectContaining({
      body: JSON.stringify({ key, password }),
      headers: expect.objectContaining({ "Accept-Language": "fr" }),
    }),
  );
});

it("recognizes reset success with an existing authenticated session", async () => {
  respond(
    { status: 200, data: { user: { id: 1 }, methods: [] }, meta: { is_authenticated: true } },
    200,
  );
  await expect(resetPassword(key, password, "fr")).resolves.toBeUndefined();
});

it.each([
  [400, { status: 400, errors: [{ code: "invalid_password_reset", param: "key" }] }, "invalidLink"],
  [
    400,
    { status: 400, errors: [{ code: "password_too_common", param: "password" }] },
    "weakPassword",
  ],
  [400, { status: 400, errors: [null] }, "unavailable"],
  [403, { status: 403 }, "unavailable"],
  [429, { status: 429 }, "rateLimited"],
  [
    401,
    { status: 401, data: { flows: [{ id: "login" }] }, meta: { is_authenticated: null } },
    "unavailable",
  ],
  [
    401,
    { status: 401, data: { flows: "login" }, meta: { is_authenticated: false } },
    "unavailable",
  ],
  [200, { status: 200 }, "unavailable"],
])("classifies reset HTTP %s with %j as %s", async (status, body, code) => {
  respond(body, status);
  await expect(resetPassword(key, password, "fr")).rejects.toMatchObject({ code });
});

it("rejects a malformed successful-looking request response", async () => {
  respond({ status: 200, errors: [{ message: "internal detail" }] }, 200);
  await expect(requestPasswordReset(email, "fr")).rejects.toMatchObject({ code: "unavailable" });
});

it("maps network failures without preserving exception text", async () => {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("internal detail")));
  await expect(requestPasswordReset(email, "fr")).rejects.toMatchObject({
    code: "unavailable",
    message: "unavailable",
  });
});
