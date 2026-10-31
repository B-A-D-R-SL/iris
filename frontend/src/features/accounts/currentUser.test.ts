// AI contribution: 50% or more AI-generated
import { describe, expect, it, vi } from "vitest";

import { fetchCurrentUser } from "./currentUser";

function respondWith(response: Response) {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response));
}

const validUser = {
  id: "00000000-0000-4000-8000-000000000001",
  name: "Camille R.",
  role: "intake_worker",
  store: null,
  language: "fr",
};

describe("fetchCurrentUser", () => {
  it("returns the signed-in user", async () => {
    respondWith(Response.json(validUser));
    await expect(fetchCurrentUser()).resolves.toEqual(validUser);
    expect(fetch).toHaveBeenCalledWith("/api/me/", expect.anything());
  });

  it.each([401, 403])("treats %d as signed out", async (status) => {
    respondWith(new Response(null, { status }));
    await expect(fetchCurrentUser()).resolves.toBeNull();
  });

  it.each([404, 500])("fails on %d so the screen can offer a retry", async (status) => {
    respondWith(new Response(null, { status }));
    await expect(fetchCurrentUser()).rejects.toThrow(`Current user unavailable: ${status}`);
  });

  it.each([
    ["an unknown role", { ...validUser, role: "superuser" }],
    ["a missing name", { ...validUser, name: undefined }],
    ["an unsupported language", { ...validUser, language: "es" }],
    ["a numeric store", { ...validUser, store: 7 }],
    ["no object", "intake_worker"],
  ])("rejects a response with %s", async (_label, body) => {
    respondWith(Response.json(body));
    await expect(fetchCurrentUser()).rejects.toThrow("Invalid current user response");
  });
});
