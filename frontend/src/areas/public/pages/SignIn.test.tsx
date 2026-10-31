// AI contribution: 50% or more AI-generated
import { QueryClient } from "@tanstack/react-query";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useLocation } from "react-router";

import App from "../../../app/App";
import type { Role } from "../../../features/accounts/currentUser";
import { expectNoAxeViolations, renderWithProviders, testUser } from "../../../test/render";

function CurrentPath() {
  const { pathname } = useLocation();
  return <output data-testid="current-path">{pathname}</output>;
}

function renderSignIn() {
  return renderWithProviders(
    <>
      <App />
      <CurrentPath />
    </>,
    { route: "/sign-in" },
  );
}

async function enterCredentials() {
  await userEvent.type(screen.getByRole("textbox", { name: "Courriel" }), "user@example.test");
  await userEvent.type(screen.getByLabelText("Mot de passe"), "correct-password");
  await userEvent.click(screen.getByRole("button", { name: "Connexion" }));
}

beforeEach(() => {
  document.cookie = "csrftoken=ready; path=/";
});

describe("US-01 sign-in screen", () => {
  it("shows a bilingual accessible form and refuses missing or malformed email", async () => {
    const { container } = renderSignIn();
    await screen.findByRole("heading", { name: "Connexion" });
    await userEvent.click(screen.getByRole("button", { name: "Connexion" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Entrez votre courriel");
    expect(screen.getByRole("alert")).toHaveTextContent("Corrigez 2 champs");
    expect(screen.getAllByText("Remplissez ce champ.")).toHaveLength(2);
    await userEvent.type(screen.getByRole("textbox", { name: "Courriel" }), "invalid");
    await userEvent.type(screen.getByLabelText("Mot de passe"), "secret");
    await userEvent.click(screen.getByRole("button", { name: "Connexion" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Entrez un courriel valide");
    await expectNoAxeViolations(container);
    await userEvent.click(screen.getByRole("button", { name: "English" }));
    expect(screen.getByRole("textbox", { name: "Email address" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sign in" })).toBeInTheDocument();
  });

  it.each([
    ["beneficiary", "/home"],
    ["store_staff", "/store"],
    ["store_manager", "/store"],
    ["intake_worker", "/staff/households"],
    ["admin", "/staff/households"],
  ] as const)("signs in %s and redirects to %s", async (role: Role, path) => {
    let signedIn = false;
    const fetchMock = vi.fn(async (input: RequestInfo | URL, options?: RequestInit) => {
      const url = String(input);
      if (url === "/api/me/") {
        return signedIn ? Response.json(testUser(role)) : new Response(null, { status: 401 });
      }
      if (url.endsWith("/auth/login") && options?.method === "POST") {
        signedIn = true;
        return Response.json({});
      }
      return new Response(null, { status: 404 });
    });
    vi.stubGlobal("fetch", fetchMock);
    renderSignIn();
    await screen.findByRole("heading", { name: "Connexion" });
    await enterCredentials();
    await waitFor(() => expect(screen.getByTestId("current-path")).toHaveTextContent(path));
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/auth/browser/v1/auth/login",
      expect.objectContaining({ method: "POST", credentials: "same-origin" }),
    );
    expect(fetchMock.mock.calls.filter(([url]) => String(url) === "/api/me/")).toHaveLength(2);
  });

  it("shows the same generic response for rejected credentials", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      if (String(input) === "/api/me/") return new Response(null, { status: 401 });
      return Response.json({ errors: [{ code: "invalid_password" }] }, { status: 401 });
    });
    vi.stubGlobal("fetch", fetchMock);
    renderSignIn();
    await screen.findByRole("heading", { name: "Connexion" });
    await enterCredentials();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Le courriel ou le mot de passe est incorrect",
    );
  });

  it("rejects a whitespace-only password without sending a sign-in request", async () => {
    const fetchMock = vi.fn(
      async (_input: RequestInfo | URL) => new Response(null, { status: 401 }),
    );
    vi.stubGlobal("fetch", fetchMock);
    renderSignIn();
    await screen.findByRole("heading", { name: "Connexion" });
    await userEvent.type(screen.getByRole("textbox", { name: "Courriel" }), "user@example.test");
    await userEvent.type(screen.getByLabelText("Mot de passe"), "   ");
    await userEvent.click(screen.getByRole("button", { name: "Connexion" }));

    expect(screen.getByRole("alert")).toHaveTextContent("Corrigez 1 champ.");
    expect(fetchMock.mock.calls.every(([url]) => String(url) === "/api/me/")).toBe(true);
  });

  it("clears previous-user cached responses before loading a new profile", async () => {
    let signedIn = false;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        if (String(input) === "/api/me/") {
          return signedIn
            ? Response.json(testUser("beneficiary"))
            : new Response(null, { status: 401 });
        }
        if (String(input).endsWith("/auth/login")) {
          signedIn = true;
          return Response.json({});
        }
        return new Response(null, { status: 404 });
      }),
    );
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    renderWithProviders(<App />, { route: "/sign-in", queryClient });
    await screen.findByRole("heading", { name: "Connexion" });
    queryClient.setQueryData(["private-list"], { items: ["previous account"] });

    await enterCredentials();

    await screen.findByRole("heading", { name: "Accueil" });
    expect(queryClient.getQueryData(["private-list"])).toBeUndefined();
  });

  it("retries the profile lookup without submitting the password again", async () => {
    let signedIn = false;
    let profileAvailable = false;
    const fetchMock = vi.fn(async (input: RequestInfo | URL, options?: RequestInit) => {
      const url = String(input);
      if (url === "/api/me/") {
        if (!signedIn) return new Response(null, { status: 401 });
        return profileAvailable
          ? Response.json(testUser("beneficiary"))
          : new Response(null, { status: 503 });
      }
      if (url.endsWith("/auth/login") && options?.method === "POST") {
        signedIn = true;
        return Response.json({});
      }
      return new Response(null, { status: 404 });
    });
    vi.stubGlobal("fetch", fetchMock);
    renderSignIn();
    await screen.findByRole("heading", { name: "Connexion" });
    await enterCredentials();
    expect(await screen.findByRole("alert")).toHaveTextContent("indisponible");

    profileAvailable = true;
    await userEvent.click(screen.getByRole("button", { name: "Réessayer" }));
    await waitFor(() => expect(screen.getByTestId("current-path")).toHaveTextContent("/home"));
    expect(
      fetchMock.mock.calls.filter(([url]) => String(url).endsWith("/auth/login")),
    ).toHaveLength(1);
  });

  it("shows the lockout notice returned by allauth", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      if (String(input) === "/api/me/") return new Response(null, { status: 401 });
      return Response.json({ errors: [{ code: "too_many_login_attempts" }] }, { status: 400 });
    });
    vi.stubGlobal("fetch", fetchMock);
    renderSignIn();
    await screen.findByRole("heading", { name: "Connexion" });
    await enterCredentials();
    expect(await screen.findByRole("alert")).toHaveTextContent("Réessayez dans 15 minutes");
  });

  it("shows the code field only after an MFA challenge, then signs in", async () => {
    let signedIn = false;
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/me/") {
        return signedIn ? Response.json(testUser("admin")) : new Response(null, { status: 401 });
      }
      if (url.endsWith("/auth/login")) {
        return Response.json({ data: { flows: [{ id: "mfa_authenticate" }] } }, { status: 401 });
      }
      if (url.endsWith("/auth/2fa/authenticate")) {
        signedIn = true;
        return Response.json({});
      }
      return new Response(null, { status: 404 });
    });
    vi.stubGlobal("fetch", fetchMock);
    renderSignIn();
    await screen.findByRole("heading", { name: "Connexion" });
    expect(screen.queryByRole("textbox", { name: "Code de vérification" })).not.toBeInTheDocument();
    await enterCredentials();
    const code = await screen.findByRole("textbox", { name: "Code de vérification" });
    await userEvent.type(code, "123456");
    await userEvent.click(screen.getByRole("button", { name: "Vérifier le code" }));
    await waitFor(() =>
      expect(screen.getByTestId("current-path")).toHaveTextContent("/staff/households"),
    );
  });

  it("revokes the session from the staff layout and returns to sign-in", async () => {
    let signedIn = true;
    const fetchMock = vi.fn(async (input: RequestInfo | URL, options?: RequestInit) => {
      const url = String(input);
      if (url === "/api/me/") {
        return signedIn ? Response.json(testUser("admin")) : new Response(null, { status: 401 });
      }
      if (url.endsWith("/auth/session") && options?.method === "DELETE") {
        signedIn = false;
        return new Response(null, { status: 401 });
      }
      return new Response(null, { status: 404 });
    });
    vi.stubGlobal("fetch", fetchMock);
    renderWithProviders(
      <>
        <App />
        <CurrentPath />
      </>,
      { route: "/staff/households" },
    );
    await screen.findByRole("heading", { name: "Foyers" });
    await userEvent.click(screen.getByRole("button", { name: "Déconnexion" }));
    await waitFor(() => expect(screen.getByTestId("current-path")).toHaveTextContent("/sign-in"));
    expect(signedIn).toBe(false);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/auth/browser/v1/auth/session",
      expect.objectContaining({ method: "DELETE" }),
    );
  });

  it.each([
    ["beneficiary", "/home"],
    ["store_staff", "/store"],
  ] as const)("offers sign-out in the %s account menu", async (role, path) => {
    let signedIn = true;
    const fetchMock = vi.fn(async (input: RequestInfo | URL, options?: RequestInit) => {
      const url = String(input);
      if (url === "/api/me/") {
        return signedIn ? Response.json(testUser(role)) : new Response(null, { status: 401 });
      }
      if (url.endsWith("/auth/session") && options?.method === "DELETE") {
        signedIn = false;
        return new Response(null, { status: 401 });
      }
      return new Response(null, { status: 404 });
    });
    vi.stubGlobal("fetch", fetchMock);
    renderWithProviders(
      <>
        <App />
        <CurrentPath />
      </>,
      { route: path },
    );
    await screen.findByRole("heading", {
      name: role === "beneficiary" ? "Accueil" : "Aujourd'hui",
    });
    await userEvent.click(screen.getByRole("button", { name: "Mon compte" }));
    await userEvent.click(screen.getByRole("menuitem", { name: "Déconnexion" }));
    await waitFor(() => expect(screen.getByTestId("current-path")).toHaveTextContent("/sign-in"));
    expect(signedIn).toBe(false);
  });

  it("keeps a failed sign-out message visible in the account menu", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, options?: RequestInit) => {
        if (String(input) === "/api/me/") return Response.json(testUser("beneficiary"));
        if (String(input).endsWith("/auth/session") && options?.method === "DELETE") {
          return new Response(null, { status: 503 });
        }
        return new Response(null, { status: 404 });
      }),
    );
    renderWithProviders(<App />, { route: "/home" });
    await screen.findByRole("heading", { name: "Accueil" });
    await userEvent.click(screen.getByRole("button", { name: "Mon compte" }));
    await userEvent.click(screen.getByRole("menuitem", { name: "Déconnexion" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("déconnexion");
    expect(screen.getByRole("menu")).toBeInTheDocument();
  });

  it("leaves protected pages when another tab signs out", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => Response.json(testUser("admin"))),
    );
    renderWithProviders(
      <>
        <App />
        <CurrentPath />
      </>,
      { route: "/staff/households" },
    );
    await screen.findByRole("heading", { name: "Foyers" });
    window.dispatchEvent(
      new StorageEvent("storage", {
        key: "iris:auth-change",
        newValue: "signed-out:other-tab",
      }),
    );
    await waitFor(() => expect(screen.getByTestId("current-path")).toHaveTextContent("/sign-in"));
  });

  it("clears cached account data after local sign-out", async () => {
    let signedIn = true;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        if (String(input) === "/api/me/") {
          return signedIn
            ? Response.json(testUser("beneficiary"))
            : new Response(null, { status: 401 });
        }
        if (String(input).endsWith("/auth/session")) {
          signedIn = false;
          return new Response(null, { status: 401 });
        }
        return new Response(null, { status: 404 });
      }),
    );
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    renderWithProviders(<App />, { route: "/home", queryClient });
    await screen.findByRole("heading", { name: "Accueil" });
    queryClient.setQueryData(["private-list"], { items: ["previous account"] });
    await userEvent.click(screen.getByRole("button", { name: "Mon compte" }));
    await userEvent.click(screen.getByRole("menuitem", { name: "Déconnexion" }));
    await waitFor(() => expect(queryClient.getQueryData(["private-list"])).toBeUndefined());
  });

  it("clears cached account data when another tab signs out", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => Response.json(testUser("admin"))),
    );
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    renderWithProviders(<App />, { route: "/staff/households", queryClient });
    await screen.findByRole("heading", { name: "Foyers" });
    queryClient.setQueryData(["private-list"], { items: ["previous account"] });
    window.dispatchEvent(
      new StorageEvent("storage", {
        key: "iris:auth-change",
        newValue: "signed-out:other-tab",
      }),
    );
    await waitFor(() => expect(queryClient.getQueryData(["private-list"])).toBeUndefined());
  });

  it("returns to a protected deep link after sign-in", async () => {
    let signedIn = false;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        if (String(input) === "/api/me/") {
          return signedIn
            ? Response.json(testUser("store_manager"))
            : new Response(null, { status: 401 });
        }
        if (String(input).endsWith("/auth/login")) {
          signedIn = true;
          return Response.json({});
        }
        return new Response(null, { status: 404 });
      }),
    );
    renderWithProviders(
      <>
        <App />
        <CurrentPath />
      </>,
      { route: "/store/listings/new" },
    );
    await screen.findByRole("heading", { name: "Connexion" });
    await enterCredentials();
    await waitFor(() =>
      expect(screen.getByTestId("current-path")).toHaveTextContent("/store/listings/new"),
    );
  });

  it("continues from an already-authenticated login response", async () => {
    let signedIn = false;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        if (String(input) === "/api/me/") {
          return signedIn
            ? Response.json(testUser("beneficiary"))
            : new Response(null, { status: 401 });
        }
        if (String(input).endsWith("/auth/login")) {
          signedIn = true;
          return Response.json({ errors: [{ code: "already_authenticated" }] }, { status: 409 });
        }
        return new Response(null, { status: 404 });
      }),
    );
    renderSignIn();
    await screen.findByRole("heading", { name: "Connexion" });
    await enterCredentials();
    await waitFor(() => expect(screen.getByTestId("current-path")).toHaveTextContent("/home"));
  });

  it("lets the user leave the MFA code step", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        if (String(input) === "/api/me/") return new Response(null, { status: 401 });
        return Response.json({ data: { flows: [{ id: "mfa_authenticate" }] } }, { status: 401 });
      }),
    );
    renderSignIn();
    await screen.findByRole("heading", { name: "Connexion" });
    await enterCredentials();
    await screen.findByRole("textbox", { name: "Code de vérification" });
    await userEvent.click(screen.getByRole("button", { name: "Utiliser un autre compte" }));
    expect(screen.getByRole("textbox", { name: "Courriel" })).toBeInTheDocument();
  });

  it("provides recovery, registration and partner links", async () => {
    renderSignIn();
    await screen.findByRole("heading", { name: "Connexion" });
    expect(screen.getByRole("link", { name: "Mot de passe oublié?" })).toHaveAttribute(
      "href",
      "/forgot-password",
    );
    expect(screen.getByRole("link", { name: "Créer un compte" })).toHaveAttribute(
      "href",
      "/sign-up",
    );
    expect(screen.getByRole("link", { name: /devenir partenaire/i })).toHaveAttribute(
      "href",
      "/partner/apply",
    );
  });
});
