// AI contribution: 50% or more AI-generated
import { QueryClient } from "@tanstack/react-query";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";

import App from "../../../app/App";
import { expectNoAxeViolations, renderWithProviders, testUser } from "../../../test/render";

const AUTH = "/api/auth/browser/v1/auth";
const REQUEST = `${AUTH}/password/request`;
const RESET = `${AUTH}/password/reset`;
const RESET_PATH = "/reset-password/test-user-test-key";
const PASSWORD = "  new-example-password  ";
const AUTH_EVENT = "iris:auth-change";
const PRIVATE_QUERY_KEY = ["private-example-data"];

function seedPrivateCache() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  queryClient.setQueryData(PRIVATE_QUERY_KEY, ["private test value"]);
  return queryClient;
}

function mockServer(path: string, responses: Response[], signedIn: () => boolean = () => false) {
  const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
    if (url === path && init?.method === "POST") {
      return responses.shift() ?? new Response(null, { status: 500 });
    }
    if (url === "/api/me/") {
      return signedIn()
        ? Response.json(testUser("beneficiary"))
        : new Response(null, { status: 401 });
    }
    return new Response(null, { status: 404 });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function resetSuccess() {
  return Response.json(
    { status: 401, data: { flows: [{ id: "login" }] }, meta: { is_authenticated: false } },
    { status: 401 },
  );
}

function authenticatedResetSuccess() {
  return Response.json({
    status: 200,
    data: { user: { id: 1 }, methods: [] },
    meta: { is_authenticated: true },
  });
}

async function fillPasswords(confirm = PASSWORD) {
  const user = userEvent.setup();
  const password = await screen.findByLabelText("Nouveau mot de passe");
  await user.type(password, PASSWORD);
  const confirmation = screen.getByLabelText("Confirmer le mot de passe");
  await user.type(confirmation, confirm);
  return { user, confirmation };
}

beforeEach(() => {
  document.cookie = "csrftoken=reset-page-test; Path=/";
  localStorage.removeItem(AUTH_EVENT);
});

it("links to the accessible request screen from sign-in in French and English", async () => {
  mockServer(REQUEST, []);
  const { container } = renderWithProviders(<App />, { route: "/sign-in" });
  await userEvent.click(await screen.findByRole("link", { name: "Mot de passe oublié?" }));
  expect(await screen.findByLabelText("Courriel")).toHaveAttribute("type", "email");
  await expectNoAxeViolations(container);
  await userEvent.click(screen.getByRole("button", { name: "English" }));
  expect(screen.getByRole("heading", { name: "Forgot your password?" })).toBeVisible();
  expect(screen.getByLabelText("Email address")).toBeVisible();
});

it.each(["existing", "missing"])(
  "shows a neutral confirmation for the %s address",
  async (name) => {
    mockServer(REQUEST, [Response.json({ status: 200 })]);
    renderWithProviders(<App />, { route: "/forgot-password" });
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "English" }));
    await user.type(screen.getByLabelText("Email address"), `${name}@example.invalid`);
    await user.click(screen.getByRole("button", { name: "Send reset link" }));
    expect(await screen.findByRole("status")).toHaveTextContent(
      "If an account uses that email address, we’ll send a password reset link.",
    );
    expect(screen.getByRole("link", { name: "Sign in" })).toHaveAttribute("href", "/sign-in");
  },
);

it("focuses the error upon a refused request, preserves editing focus, and allows retry", async () => {
  mockServer(REQUEST, [
    Response.json({ status: 429 }, { status: 429 }),
    Response.json({ status: 200 }),
  ]);
  renderWithProviders(<App />, { route: "/forgot-password" });
  const user = userEvent.setup();
  const email = await screen.findByLabelText("Courriel");
  const submit = screen.getByRole("button", { name: "Envoyer le lien de réinitialisation" });
  await user.type(email, "reset@example.invalid");
  await user.click(submit);
  const alert = await screen.findByRole("alert");
  expect(alert).toHaveTextContent("Trop de tentatives");
  expect(alert.closest('[tabindex="-1"]')).toHaveFocus();
  await user.type(email, "x");
  expect(email).toHaveFocus();
  await user.click(submit);
  expect(await screen.findByRole("status")).toHaveTextContent("Si un compte utilise ce courriel");
});

it("labels both reset passwords accessibly in French and English", async () => {
  mockServer(RESET, []);
  const { container } = renderWithProviders(<App />, { route: RESET_PATH });
  expect(await screen.findByLabelText("Nouveau mot de passe")).toHaveAttribute(
    "autocomplete",
    "new-password",
  );
  await expectNoAxeViolations(container);
  await userEvent.click(screen.getByRole("button", { name: "English" }));
  expect(screen.getByLabelText("New password")).toBeVisible();
  expect(screen.getByLabelText("Confirm password")).toBeVisible();
});

it("rejects a mismatched confirmation before submitting and keeps focus while correcting it", async () => {
  const fetchMock = mockServer(RESET, []);
  renderWithProviders(<App />, { route: RESET_PATH });
  const { user, confirmation } = await fillPasswords("mismatch");
  await user.click(screen.getByRole("button", { name: "Réinitialiser mon mot de passe" }));
  const alert = await screen.findByRole("alert");
  expect(alert.closest('[tabindex="-1"]')).toHaveFocus();
  expect(confirmation).toHaveAttribute("aria-invalid", "true");
  expect(fetchMock.mock.calls.some(([url]) => url === RESET)).toBe(false);
  await user.type(confirmation, "x");
  expect(confirmation).toHaveFocus();
});

it("offers a new link after an invalid key without displaying server text", async () => {
  mockServer(RESET, [
    Response.json(
      {
        status: 400,
        errors: [{ code: "invalid_password_reset", param: "key", message: "private server text" }],
      },
      { status: 400 },
    ),
  ]);
  renderWithProviders(<App />, { route: RESET_PATH });
  const { user } = await fillPasswords();
  await user.click(screen.getByRole("button", { name: "Réinitialiser mon mot de passe" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Ce lien de réinitialisation est invalide ou a expiré.",
  );
  expect(screen.queryByText("private server text")).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Demander un nouveau lien" })).toHaveAttribute(
    "href",
    "/forgot-password",
  );
});

it("offers sign-in after signed-out reset success without submitting a login", async () => {
  const fetchMock = mockServer(RESET, [resetSuccess()]);
  renderWithProviders(<App />, { route: RESET_PATH });
  const { user } = await fillPasswords();
  await user.click(screen.getByRole("button", { name: "Réinitialiser mon mot de passe" }));
  expect(await screen.findByRole("status")).toHaveTextContent(
    "Votre mot de passe a été réinitialisé.",
  );
  expect(screen.getByRole("link", { name: "Connexion" })).toHaveAttribute("href", "/sign-in");
  expect(fetchMock.mock.calls.some(([url]) => url === `${AUTH}/login`)).toBe(false);
  expect(localStorage.getItem(AUTH_EVENT)).toBeNull();
});

it("preserves an existing session without submitting sign-out or account switching", async () => {
  const fetchMock = mockServer(RESET, [authenticatedResetSuccess()], () => true);
  const queryClient = seedPrivateCache();
  renderWithProviders(<App />, { route: RESET_PATH, queryClient });
  const { user } = await fillPasswords();
  await user.click(screen.getByRole("button", { name: "Réinitialiser mon mot de passe" }));
  expect(
    await screen.findByText(/Vous êtes toujours connecté à votre compte actuel/),
  ).toBeVisible();
  expect(screen.getByRole("button", { name: "Déconnexion" })).toBeVisible();
  expect(fetchMock.mock.calls.filter(([, init]) => init?.method)).toHaveLength(1);
  expect(queryClient.getQueryData(PRIVATE_QUERY_KEY)).toEqual(["private test value"]);
  expect(localStorage.getItem(AUTH_EVENT)).toBeNull();
});

it("offers sign-in when resetting the current account invalidates its browser session", async () => {
  const responses = [authenticatedResetSuccess()];
  mockServer(RESET, responses, () => responses.length > 0);
  const queryClient = seedPrivateCache();
  renderWithProviders(<App />, { route: RESET_PATH, queryClient });
  expect(await screen.findByRole("button", { name: "Déconnexion" })).toBeVisible();
  const { user } = await fillPasswords();
  await user.click(screen.getByRole("button", { name: "Réinitialiser mon mot de passe" }));
  expect(await screen.findByRole("link", { name: "Connexion" })).toHaveAttribute(
    "href",
    "/sign-in",
  );
  expect(screen.queryByRole("button", { name: "Déconnexion" })).not.toBeInTheDocument();
  expect(queryClient.getQueryData(PRIVATE_QUERY_KEY)).toBeUndefined();
  expect(localStorage.getItem(AUTH_EVENT)).toMatch(/^signed-out:/);
});

it("clears private data and notifies other tabs when the post-reset profile refresh fails", async () => {
  const responses = [authenticatedResetSuccess()];
  mockServer(RESET, responses, () => true);
  const original = vi.mocked(fetch);
  original.mockImplementation(async (url, init) => {
    if (url === "/api/me/" && responses.length === 0) throw new Error("offline");
    if (url === RESET && init?.method === "POST") return responses.shift()!;
    return Response.json(testUser("beneficiary"));
  });
  const queryClient = seedPrivateCache();
  renderWithProviders(<App />, { route: RESET_PATH, queryClient });
  expect(await screen.findByRole("button", { name: "Déconnexion" })).toBeVisible();
  const { user } = await fillPasswords();
  await user.click(screen.getByRole("button", { name: "Réinitialiser mon mot de passe" }));
  expect(await screen.findByRole("link", { name: "Connexion" })).toBeVisible();
  expect(queryClient.getQueryData(PRIVATE_QUERY_KEY)).toBeUndefined();
  expect(localStorage.getItem(AUTH_EVENT)).toMatch(/^signed-out:/);
});

it("clears private data if a background refresh signed the user out before reset completion", async () => {
  const responses = [authenticatedResetSuccess()];
  mockServer(RESET, responses, () => responses.length > 0);
  const queryClient = seedPrivateCache();
  renderWithProviders(<App />, { route: RESET_PATH, queryClient });
  expect(await screen.findByRole("button", { name: "Déconnexion" })).toBeVisible();
  const { user } = await fillPasswords();
  queryClient.setQueryData(["current-user"], null);
  await user.click(screen.getByRole("button", { name: "Réinitialiser mon mot de passe" }));
  expect(await screen.findByRole("link", { name: "Connexion" })).toBeVisible();
  expect(queryClient.getQueryData(PRIVATE_QUERY_KEY)).toBeUndefined();
  expect(localStorage.getItem(AUTH_EVENT)).toMatch(/^signed-out:/);
});
