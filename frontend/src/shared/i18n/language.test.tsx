// AI contribution: 50% or more AI-generated
/** US-08: French or English on every page, saved on the account and kept across visits. */
import { QueryClient } from "@tanstack/react-query";
import { act, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "../../app/App";
import { mockCurrentUser, renderWithProviders, testUser } from "../../test/render";
import { CURRENT_USER_QUERY_KEY, type CurrentUser } from "../auth/currentUser";
import type { Role } from "../auth/roles";
import { logger } from "../logger";
import i18n from ".";
import { rememberLanguage, storedLanguage } from "./languagePreference";

const STORAGE_KEY = "iris:language";

beforeEach(() => localStorage.clear());
afterEach(() => vi.restoreAllMocks());

/** Answers /api/me/ for this user; PATCH answers with `patched` (the saved account). */
function mockAccount(
  user: CurrentUser,
  patched: (init: RequestInit) => Response | Promise<Response> = () => Response.json(user),
) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
    if (url === "/api/staff/households/" && init?.method === "HEAD") {
      return new Response(null, { status: 200 });
    }
    if (!url.endsWith("/api/me/")) return new Response(null, { status: 404 });
    return init?.method === "PATCH" ? patched(init) : Response.json(user);
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

const patches = (fetchMock: ReturnType<typeof vi.fn>) =>
  fetchMock.mock.calls.filter(([, init]) => (init as RequestInit | undefined)?.method === "PATCH");

/** A PATCH answer the test releases itself, to hold a save in flight. */
function heldAnswer() {
  let release: (response: Response) => void = () => undefined;
  const answer = new Promise<Response>((resolve) => {
    release = resolve;
  });
  return { answer, release };
}

const sentLanguage = (init: RequestInit) =>
  (JSON.parse(init.body as string) as { language: string }).language;

// rule: BR-LANG-001
describe("the language a browser remembers", () => {
  it("is French by default", () => {
    expect(storedLanguage()).toBe("fr");
  });

  it("is the last language chosen in this browser", () => {
    localStorage.setItem(STORAGE_KEY, "en");
    expect(storedLanguage()).toBe("en");
  });

  it.each(["de", "EN", ""])("ignores a stored value that is not fr or en (%j)", (value) => {
    localStorage.setItem(STORAGE_KEY, value);
    expect(storedLanguage()).toBe("fr");
  });

  it("falls back to French when the browser blocks storage, and logs it", () => {
    const warning = vi.spyOn(logger, "warning").mockImplementation(() => undefined);
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new DOMException("blocked", "SecurityError");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("blocked", "SecurityError");
    });
    expect(storedLanguage()).toBe("fr");
    expect(() => rememberLanguage("en")).not.toThrow();
    expect(warning.mock.calls).toEqual([
      ["language_storage_unavailable"],
      ["language_storage_unavailable"],
    ]);
  });

  it("stores only fr or en", () => {
    rememberLanguage("de");
    expect(localStorage.getItem(STORAGE_KEY)).toBeNull();
  });

  it("follows every switch and keeps the page's lang attribute in step", async () => {
    await i18n.changeLanguage("en");
    expect(localStorage.getItem(STORAGE_KEY)).toBe("en");
    expect(document.documentElement.lang).toBe("en");
    await i18n.changeLanguage("fr");
    expect(localStorage.getItem(STORAGE_KEY)).toBe("fr");
    expect(document.documentElement.lang).toBe("fr");
  });
});

// rule: BR-LANG-001
describe("the language switch is on every page", () => {
  it.each([
    ["/", "signed-out"],
    ["/sign-in", "signed-out"],
    ["/partner/apply", "signed-out"],
    ["/privacy", "signed-out"],
    ["/nowhere", "signed-out"],
    ["/staff/households", "intake_worker"],
    ["/staff/walk-in", "intake_worker"],
    ["/staff/partners", "admin"],
  ] as const)("in the top bar of %s (%s)", async (route, user) => {
    mockCurrentUser(user === "signed-out" ? user : testUser(user));
    renderWithProviders(<App />, { route });
    await userEvent.click(await screen.findByRole("button", { name: "English" }));
    expect(await screen.findByRole("button", { name: "Français" })).toBeInTheDocument();
    expect(document.documentElement.lang).toBe("en");
  });

  it.each([
    ["/listings", "beneficiary"],
    ["/store/listings/new", "store_staff"],
    ["/store/listings/new", "store_manager"],
  ] as const)("in the account menu of %s (%s)", async (route, role: Role) => {
    mockCurrentUser(testUser(role));
    renderWithProviders(<App />, { route });
    await userEvent.click(await screen.findByRole("button", { name: "Mon compte" }));
    await userEvent.click(await screen.findByRole("menuitem", { name: "English" }));
    expect(await screen.findByRole("button", { name: "My account" })).toBeInTheDocument();
  });
});

// rule: BR-LANG-001, BR-LANG-002
describe("a signed-out visitor's choice", () => {
  it("opens in French on a first visit", async () => {
    mockCurrentUser("signed-out");
    renderWithProviders(<App />, { route: "/" });
    expect(await screen.findByRole("heading", { name: "Bienvenue sur Iris" })).toBeInTheDocument();
    expect(document.documentElement.lang).toBe("fr");
  });

  it("is kept in the browser and never sent to the server", async () => {
    const fetchMock = mockCurrentUser("signed-out");
    renderWithProviders(<App />, { route: "/" });
    await userEvent.click(await screen.findByRole("button", { name: "English" }));
    expect(await screen.findByRole("heading", { name: "Welcome to Iris" })).toBeInTheDocument();
    expect(localStorage.getItem(STORAGE_KEY)).toBe("en");
    expect(patches(fetchMock)).toEqual([]);
  });
});

// rule: BR-LANG-002
describe("a signed-in user's choice is saved on the account", () => {
  it.each([
    ["beneficiary", "/listings", "menu"],
    ["store_staff", "/store/listings/new", "menu"],
    ["store_manager", "/store/listings/new", "menu"],
    ["intake_worker", "/staff/households", "bar"],
    ["admin", "/staff/partners", "bar"],
  ] as const)("is saved on the %s's account", async (role, route, place) => {
    const user = testUser(role);
    const fetchMock = mockAccount(user, () => Response.json({ ...user, language: "en" }));
    document.cookie = "csrftoken=test-csrf-token";
    renderWithProviders(<App />, { route });
    if (place === "menu") {
      await userEvent.click(await screen.findByRole("button", { name: "Mon compte" }));
      await userEvent.click(await screen.findByRole("menuitem", { name: "English" }));
    } else {
      await userEvent.click(await screen.findByRole("button", { name: "English" }));
    }

    await waitFor(() => expect(patches(fetchMock)).toHaveLength(1));
    const [url, init] = patches(fetchMock)[0] as [string, RequestInit];
    expect(url).toBe("/api/me/");
    expect(JSON.parse(init.body as string)).toEqual({ language: "en" });
    expect(new Headers(init.headers).get("X-CSRFToken")).toBe("test-csrf-token");
    expect(new Headers(init.headers).get("X-Account-Id")).toBe(user.id);
    expect(i18n.resolvedLanguage).toBe("en");
  });
});

// rule: BR-LANG-001
describe("the account's language after sign-in", () => {
  it("is used as soon as the account loads, whatever this browser chose before", async () => {
    localStorage.setItem(STORAGE_KEY, "fr");
    mockAccount(testUser("intake_worker", { language: "en" }));
    renderWithProviders(<App />, { route: "/staff/households" });
    expect(await screen.findByRole("button", { name: "Français" })).toBeInTheDocument();
    expect(localStorage.getItem(STORAGE_KEY)).toBe("en");
  });

  it("is applied again when another account signs in", async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    mockAccount(testUser("admin"));
    renderWithProviders(<App />, { route: "/staff/partners", queryClient });
    expect(await screen.findByRole("button", { name: "English" })).toBeInTheDocument();

    act(() => queryClient.setQueryData(CURRENT_USER_QUERY_KEY, null));
    act(() =>
      queryClient.setQueryData(
        CURRENT_USER_QUERY_KEY,
        testUser("admin", { id: "00000000-0000-4000-8000-000000000002", language: "en" }),
      ),
    );
    expect(await screen.findByRole("button", { name: "Français" })).toBeInTheDocument();
  });
});

// rule: BR-LANG-002
describe("a language save that fails", () => {
  it.each([
    ["is refused", () => new Response(null, { status: 500 }), { statusCode: 500 }],
    ["gets no answer", () => Promise.reject(new TypeError("offline")), { statusCode: null }],
  ])("stays on screen when the save %s, and logs why", async (_case, answer, context) => {
    const warning = vi.spyOn(logger, "warning").mockImplementation(() => undefined);
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    mockAccount(testUser("intake_worker"), answer);
    renderWithProviders(<App />, { route: "/staff/households", queryClient });
    await userEvent.click(await screen.findByRole("button", { name: "English" }));

    await waitFor(() => expect(warning).toHaveBeenCalledWith("language_save_failed", context));
    await act(() => queryClient.invalidateQueries({ queryKey: CURRENT_USER_QUERY_KEY }));
    expect(screen.getByRole("button", { name: "Français" })).toBeInTheDocument();
    expect(queryClient.getQueryData<CurrentUser>(CURRENT_USER_QUERY_KEY)?.language).toBe("fr");
  });

  it("logs an account response that is not a valid user as its own event", async () => {
    const warning = vi.spyOn(logger, "warning").mockImplementation(() => undefined);
    mockAccount(testUser("admin"), () => Response.json({ language: "de" }));
    renderWithProviders(<App />, { route: "/staff/partners" });
    await userEvent.click(await screen.findByRole("button", { name: "English" }));
    await waitFor(() => expect(warning).toHaveBeenCalledWith("language_save_response_invalid"));
    expect(warning).not.toHaveBeenCalledWith("language_save_failed", expect.anything());
  });

  it("gives up after 15 seconds without an answer", async () => {
    const timeout = vi.spyOn(AbortSignal, "timeout");
    const fetchMock = mockAccount(testUser("admin"));
    renderWithProviders(<App />, { route: "/staff/partners" });
    await userEvent.click(await screen.findByRole("button", { name: "English" }));
    await waitFor(() => expect(patches(fetchMock)).toHaveLength(1));
    expect(timeout).toHaveBeenCalledWith(15_000);
    expect((patches(fetchMock)[0]?.[1] as RequestInit).signal).toBeInstanceOf(AbortSignal);
  });
});

// rule: BR-LANG-002
describe("a choice made while the account is still loading", () => {
  /** /api/me/ answers only when the test releases it; PATCH answers with the saved account. */
  function mockLoadingAccount() {
    const me = heldAnswer();
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
      if (!url.endsWith("/api/me/")) return new Response(null, { status: 404 });
      if (init?.method !== "PATCH") return (await me.answer).clone();
      return Response.json(testUser("beneficiary", { language: sentLanguage(init) as "en" }));
    });
    vi.stubGlobal("fetch", fetchMock);
    return { fetchMock, release: me.release };
  }

  it("is saved once the account loads, and the screen stays in it", async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const { fetchMock, release } = mockLoadingAccount();
    renderWithProviders(<App />, { route: "/privacy", queryClient });
    await userEvent.click(await screen.findByRole("button", { name: "English" }));

    release(Response.json(testUser("beneficiary", { language: "fr" })));
    await waitFor(() => expect(patches(fetchMock)).toHaveLength(1));
    expect(sentLanguage(patches(fetchMock)[0]?.[1] as RequestInit)).toBe("en");
    await waitFor(() =>
      expect(queryClient.getQueryData<CurrentUser>(CURRENT_USER_QUERY_KEY)?.language).toBe("en"),
    );
    expect(screen.getByRole("button", { name: "Français" })).toBeInTheDocument();
  });

  it("stays in the browser when the account turns out to be signed out", async () => {
    const warning = vi.spyOn(logger, "warning");
    const { fetchMock, release } = mockLoadingAccount();
    renderWithProviders(<App />, { route: "/privacy" });
    await userEvent.click(await screen.findByRole("button", { name: "English" }));

    release(new Response(null, { status: 401 }));
    expect(await screen.findByRole("button", { name: "Français" })).toBeInTheDocument();
    expect(localStorage.getItem(STORAGE_KEY)).toBe("en");
    expect(patches(fetchMock)).toEqual([]);
    // A sign-out is not a failure: nothing is logged for it.
    await waitFor(() => expect(i18n.resolvedLanguage).toBe("en"));
    expect(warning).not.toHaveBeenCalledWith("language_account_unavailable");
  });
});

// rule: BR-LANG-002
describe("quick language switches", () => {
  it("saves quick switches one after another, so the account keeps the last choice", async () => {
    const user = testUser("intake_worker");
    const first = heldAnswer();
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const fetchMock = mockAccount(user, (init) =>
      sentLanguage(init) === "en" ? first.answer : Response.json({ ...user, language: "fr" }),
    );
    renderWithProviders(<App />, { route: "/staff/households", queryClient });
    await userEvent.click(await screen.findByRole("button", { name: "English" }));
    await userEvent.click(await screen.findByRole("button", { name: "Français" }));

    // The second save waits for the first, even though the user already chose again.
    expect(patches(fetchMock)).toHaveLength(1);
    first.release(Response.json({ ...user, language: "en" }));

    await waitFor(() => expect(patches(fetchMock)).toHaveLength(2));
    expect(patches(fetchMock).map(([, init]) => sentLanguage(init as RequestInit))).toEqual([
      "en",
      "fr",
    ]);
    await waitFor(() =>
      expect(queryClient.getQueryData<CurrentUser>(CURRENT_USER_QUERY_KEY)?.language).toBe("fr"),
    );
  });
});

// rule: BR-LANG-002
describe("a language save while the account changes", () => {
  it("does not bring back an account that signed out while its save was running", async () => {
    const user = testUser("admin");
    const held = heldAnswer();
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const fetchMock = mockAccount(user, () => held.answer);
    renderWithProviders(<App />, { route: "/staff/partners", queryClient });
    await userEvent.click(await screen.findByRole("button", { name: "English" }));
    await waitFor(() => expect(patches(fetchMock)).toHaveLength(1));

    act(() => queryClient.setQueryData(CURRENT_USER_QUERY_KEY, null));
    await act(async () => {
      held.release(Response.json({ ...user, language: "en" }));
      await held.answer;
    });

    await waitFor(() => expect(queryClient.getQueryData(CURRENT_USER_QUERY_KEY)).toBeNull());
  });

  it("drops a queued save when another account signs in before it is sent", async () => {
    const first = testUser("admin");
    const second = testUser("admin", { id: "00000000-0000-4000-8000-000000000002" });
    const held = heldAnswer();
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const fetchMock = mockAccount(first, () => held.answer);
    renderWithProviders(<App />, { route: "/staff/partners", queryClient });
    await userEvent.click(await screen.findByRole("button", { name: "English" }));
    await userEvent.click(await screen.findByRole("button", { name: "Français" }));
    expect(patches(fetchMock)).toHaveLength(1);

    act(() => queryClient.setQueryData(CURRENT_USER_QUERY_KEY, null));
    act(() => queryClient.setQueryData(CURRENT_USER_QUERY_KEY, second));
    await act(async () => {
      held.release(Response.json({ ...first, language: "en" }));
      await held.answer;
      // Let the first save finish and the queued one run.
      await new Promise((resolve) => setTimeout(resolve, 50));
    });

    // The queued "fr" save for the first account is never sent with the second's session.
    await waitFor(() => expect(queryClient.getQueryData(CURRENT_USER_QUERY_KEY)).toEqual(second));
    expect(patches(fetchMock)).toHaveLength(1);
  });
});

// rule: BR-LANG-002
describe("a language save another tab overtook", () => {
  it("names its account, so a session another tab switched to account B is refused", async () => {
    const warning = vi.spyOn(logger, "warning").mockImplementation(() => undefined);
    const first = testUser("intake_worker");
    let sessionAccount = first.id;
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    // The server refuses a save named for an account the session no longer holds.
    const fetchMock = mockAccount(first, (init) =>
      new Headers(init.headers).get("X-Account-Id") === sessionAccount
        ? Response.json({ ...first, language: "en" })
        : Response.json({ code: "account_changed", message: "", fields: {} }, { status: 409 }),
    );
    renderWithProviders(<App />, { route: "/staff/households", queryClient });
    await screen.findByRole("button", { name: "English" });

    // Another tab signs in account B; this tab still shows account A.
    sessionAccount = "00000000-0000-4000-8000-000000000002";
    await userEvent.click(screen.getByRole("button", { name: "English" }));

    await waitFor(() =>
      expect(warning).toHaveBeenCalledWith("language_save_failed", { statusCode: 409 }),
    );
    const [, init] = patches(fetchMock)[0] as [string, RequestInit];
    expect(new Headers(init.headers).get("X-Account-Id")).toBe(first.id);
    expect(queryClient.getQueryData<CurrentUser>(CURRENT_USER_QUERY_KEY)).toEqual(first);
  });
});

// rule: BR-LANG-002
describe("the save queue", () => {
  it("belongs to one app, so a save never answered there holds no other app back", async () => {
    const stuck = mockAccount(testUser("admin"), () => new Promise<Response>(() => undefined));
    const first = renderWithProviders(<App />, { route: "/staff/partners" });
    await userEvent.click(await screen.findByRole("button", { name: "English" }));
    await waitFor(() => expect(patches(stuck)).toHaveLength(1));
    first.unmount();

    await i18n.changeLanguage("fr");
    const fetchMock = mockAccount(testUser("admin"));
    renderWithProviders(<App />, { route: "/staff/partners" });
    await userEvent.click(await screen.findByRole("button", { name: "English" }));
    await waitFor(() => expect(patches(fetchMock)).toHaveLength(1));
  });
});

// rule: BR-LANG-002
describe("after a choice made while the account loads", () => {
  /** A server keeping the account's language; /api/me/ answers once released. */
  function mockServer(failLanguage: string | null) {
    const me = heldAnswer();
    let saved = "fr";
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
      if (!url.endsWith("/api/me/")) return new Response(null, { status: 404 });
      if (init?.method === "PATCH") {
        if (sentLanguage(init) === failLanguage) return new Response(null, { status: 500 });
        saved = sentLanguage(init);
      }
      const answer = await me.answer;
      return answer.ok
        ? Response.json(testUser("beneficiary", { language: saved as "fr" }))
        : answer;
    });
    vi.stubGlobal("fetch", fetchMock);
    return { fetchMock, release: me.release };
  }

  it("caches what the server last confirmed when a later save fails", async () => {
    vi.spyOn(logger, "warning").mockImplementation(() => undefined);
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const { fetchMock, release } = mockServer("fr");
    renderWithProviders(<App />, { route: "/privacy", queryClient });
    await userEvent.click(await screen.findByRole("button", { name: "English" }));
    await userEvent.click(await screen.findByRole("button", { name: "Français" }));

    release(Response.json({}));
    await waitFor(() => expect(patches(fetchMock)).toHaveLength(2));
    // "en" was saved, then "fr" failed: the account is read again and is "en".
    await waitFor(() =>
      expect(queryClient.getQueryData<CurrentUser>(CURRENT_USER_QUERY_KEY)?.language).toBe("en"),
    );
  });

  it("logs an account that could not be read, and keeps the choice in the browser", async () => {
    const warning = vi.spyOn(logger, "warning").mockImplementation(() => undefined);
    const { fetchMock, release } = mockServer(null);
    renderWithProviders(<App />, { route: "/privacy" });
    await userEvent.click(await screen.findByRole("button", { name: "English" }));

    release(new Response(null, { status: 500 }));
    await waitFor(() => expect(warning).toHaveBeenCalledWith("language_account_unavailable"));
    expect(localStorage.getItem(STORAGE_KEY)).toBe("en");
    expect(patches(fetchMock)).toEqual([]);
  });
});
