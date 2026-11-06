// AI contribution: 50% or more AI-generated
import { act, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useLocation } from "react-router";

import App from "../../../app/App";
import { expectNoAxeViolations, renderWithProviders, testUser } from "../../../test/render";

const ACCEPT = "/api/invitations/accept/";
// A deterministic token made from 32 synthetic bytes, never a real invitation.
const TOKEN = btoa("t".repeat(32)).replaceAll("=", "");
const PASSWORD = "Invitation-test-429";
const SUBMIT = /(?:définir|créer).*mot de passe/i;
const PASSWORD_ERROR = "Choisissez un mot de passe moins courant.";

/** Observe real router navigation without replacing the page under test. */
function CurrentPath() {
  return <output data-testid="current-path">{useLocation().pathname}</output>;
}

/** Mock only HTTP, leaving routing, forms and session providers real. */
function mockAcceptance(
  respond: () => Promise<Response> = async () => new Response(null, { status: 200 }),
) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, options?: RequestInit) => {
    const url = String(input);
    if (url === ACCEPT && options?.method === "POST") return respond();
    return new Response(null, { status: url === "/api/me/" ? 401 : 404 });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

/** Count submissions independently of the provider's current-user requests. */
function acceptanceCalls(fetchMock: ReturnType<typeof mockAcceptance>) {
  return fetchMock.mock.calls.filter(
    ([url, options]) => String(url) === ACCEPT && options?.method === "POST",
  );
}

/** Exercise the actual public route that #431 introduces. */
function renderInvitation() {
  return renderWithProviders(
    <>
      <App />
      <CurrentPath />
    </>,
    { route: `/invitation/${TOKEN}` },
  );
}

/** Fill the French form with generated credentials or a validation boundary. */
async function fillPasswords(password = PASSWORD, confirmation = password) {
  const user = userEvent.setup();
  const first = await screen.findByLabelText(/^Mot de passe$/);
  if (password) await user.type(first, password);
  if (confirmation)
    await user.type(screen.getByLabelText(/^Confirmer le mot de passe$/), confirmation);
  return user;
}

beforeEach(() => {
  document.cookie = "csrftoken=invitation-csrf-test; path=/";
});

describe("US-04 accept an invitation and set a password", () => {
  it("shows accessible password and confirmation fields in French and English", async () => {
    mockAcceptance();
    const { container } = renderInvitation();
    await screen.findByLabelText(/^Mot de passe$/);
    expect(screen.getByLabelText(/^Confirmer le mot de passe$/)).toHaveAttribute(
      "type",
      "password",
    );
    expect(screen.getByRole("button", { name: SUBMIT })).toBeInTheDocument();
    await expectNoAxeViolations(container);

    await userEvent.click(screen.getByRole("button", { name: "English" }));
    expect(screen.getByLabelText(/^Password$/)).toBeInTheDocument();
    expect(screen.getByLabelText(/^Confirm password$/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /(?:set|create).*password/i })).toBeInTheDocument();
  });

  it.each([
    ["missing passwords", "", ""],
    ["a short password", "short", "short"],
    ["different confirmations", PASSWORD, `${PASSWORD}-different`],
  ])("refuses %s before sending a request", async (caseName, password, confirmation) => {
    const fetchMock = mockAcceptance();
    renderInvitation();
    const user = await fillPasswords(password, confirmation);
    await user.click(screen.getByRole("button", { name: SUBMIT }));

    expect(await screen.findByRole("alert")).toBeVisible();
    expect(acceptanceCalls(fetchMock), caseName).toHaveLength(0);
    expect(screen.getByLabelText(/^Mot de passe$/)).toHaveValue(password);
  });

  it("refocuses repeated local failures without interrupting password editing", async () => {
    const fetchMock = mockAcceptance();
    renderInvitation();
    const user = await fillPasswords("", "");
    const submit = screen.getByRole("button", { name: SUBMIT });
    await user.click(submit);
    expect((await screen.findByRole("alert")).closest('[tabindex="-1"]')).toHaveFocus();

    await user.click(submit);
    expect(screen.getByRole("alert").closest('[tabindex="-1"]')).toHaveFocus();
    const password = screen.getByLabelText(/^Mot de passe$/);
    await user.type(password, PASSWORD);
    expect(password).toHaveFocus();
    expect(password).toHaveValue(PASSWORD);

    const confirmation = screen.getByLabelText(/^Confirmer le mot de passe$/);
    await user.click(confirmation);
    await user.type(confirmation, `${PASSWORD}-different`);
    expect(confirmation).toHaveFocus();
    expect(confirmation).toHaveValue(`${PASSWORD}-different`);
    await user.click(submit);

    expect(screen.getByRole("alert").closest('[tabindex="-1"]')).toHaveFocus();
    expect(acceptanceCalls(fetchMock)).toHaveLength(0);
  });

  it("sends the route token and password with CSRF and language, then opens sign-in", async () => {
    const fetchMock = mockAcceptance();
    renderInvitation();
    await screen.findByLabelText(/^Mot de passe$/);
    await userEvent.click(screen.getByRole("button", { name: "English" }));
    await userEvent.type(screen.getByLabelText(/^Password$/), PASSWORD);
    await userEvent.type(screen.getByLabelText(/^Confirm password$/), PASSWORD);
    await userEvent.click(screen.getByRole("button", { name: /(?:set|create).*password/i }));

    await waitFor(() => expect(screen.getByTestId("current-path")).toHaveTextContent("/sign-in"));
    const calls = acceptanceCalls(fetchMock);
    expect(calls).toHaveLength(1);
    const options = calls[0][1]!;
    expect(JSON.parse(String(options.body))).toEqual({ token: TOKEN, password: PASSWORD });
    expect(options.credentials).toBe("same-origin");
    const headers = new Headers(options.headers);
    expect(headers.get("X-CSRFToken")).toBe("invitation-csrf-test");
    expect(headers.get("Accept-Language")).toBe("en");
    expect(headers.get("Content-Type")).toBe("application/json");
    expect(fetchMock.mock.calls.some(([url]) => String(url).endsWith("/auth/login"))).toBe(false);
  });

  it.each([
    ["invitation_expired", "Ce lien d’invitation a expiré."],
    ["invitation_used", "Ce lien d’invitation a déjà été utilisé."],
    ["invitation_invalid", "Ce lien d’invitation est invalide."],
    ["email_already_registered", "Un compte utilise déjà ce courriel."],
  ])("explains %s without exposing the token", async (code, message) => {
    const fetchMock = mockAcceptance(async () =>
      Response.json({ code, message, fields: {} }, { status: 400 }),
    );
    renderInvitation();
    const user = await fillPasswords();
    await user.click(screen.getByRole("button", { name: SUBMIT }));

    expect(await screen.findByRole("alert")).toHaveTextContent(message);
    expect(screen.getByRole("alert")).not.toHaveTextContent(TOKEN);
    expect(screen.getByTestId("current-path")).toHaveTextContent(`/invitation/${TOKEN}`);
    expect(acceptanceCalls(fetchMock)).toHaveLength(1);
  });

  it("keeps entered values after a service failure and permits retry", async () => {
    let attempts = 0;
    const fetchMock = mockAcceptance(
      async () => new Response(null, { status: ++attempts === 1 ? 503 : 200 }),
    );
    renderInvitation();
    const user = await fillPasswords();
    await user.click(screen.getByRole("button", { name: SUBMIT }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/indisponible|réessay/i);
    expect(screen.getByLabelText(/^Mot de passe$/)).toHaveValue(PASSWORD);
    expect(screen.getByLabelText(/^Confirmer le mot de passe$/)).toHaveValue(PASSWORD);
    await user.click(screen.getByRole("button", { name: SUBMIT }));

    await waitFor(() => expect(screen.getByTestId("current-path")).toHaveTextContent("/sign-in"));
    expect(acceptanceCalls(fetchMock)).toHaveLength(2);
  });

  it("shows backend password errors under the field and focuses the error summary", async () => {
    const fetchMock = mockAcceptance(async () =>
      Response.json(
        {
          code: "validation_error",
          message: "Vérifiez les champs indiqués.",
          fields: { password: [PASSWORD_ERROR] },
        },
        { status: 400 },
      ),
    );
    renderInvitation();
    const user = await fillPasswords();
    await user.click(screen.getByRole("button", { name: SUBMIT }));

    const alert = await screen.findByRole("alert");
    const summary = alert.closest('[tabindex="-1"]') ?? alert;
    expect(summary).toHaveFocus();
    const password = screen.getByLabelText(/^Mot de passe$/);
    expect(password).toHaveAttribute("aria-invalid", "true");
    expect(password).toHaveAccessibleDescription(/Choisissez un mot de passe moins courant/);
    expect(password).toHaveValue(PASSWORD);
    expect(screen.getByLabelText(/^Confirmer le mot de passe$/)).toHaveValue(PASSWORD);
    expect(acceptanceCalls(fetchMock)).toHaveLength(1);
  });

  it("refocuses repeated server failures without interrupting password editing", async () => {
    const fetchMock = mockAcceptance(async () =>
      Response.json(
        {
          code: "validation_error",
          message: "Vérifiez les champs indiqués.",
          fields: { password: [PASSWORD_ERROR] },
        },
        { status: 400 },
      ),
    );
    renderInvitation();
    const user = await fillPasswords();
    const submit = screen.getByRole("button", { name: SUBMIT });
    await user.click(submit);
    expect((await screen.findByRole("alert")).closest('[tabindex="-1"]')).toHaveFocus();

    const password = screen.getByLabelText(/^Mot de passe$/);
    await user.type(password, "-retry");
    expect(password).toHaveFocus();
    expect(password).toHaveValue(`${PASSWORD}-retry`);
    const confirmation = screen.getByLabelText(/^Confirmer le mot de passe$/);
    await user.type(confirmation, "-retry");
    expect(confirmation).toHaveFocus();
    expect(confirmation).toHaveValue(`${PASSWORD}-retry`);
    await user.click(submit);

    await waitFor(() => {
      expect(screen.getByRole("alert").closest('[tabindex="-1"]')).toHaveFocus();
    });
    expect(acceptanceCalls(fetchMock)).toHaveLength(2);
    expect(password).toHaveValue(`${PASSWORD}-retry`);
    expect(confirmation).toHaveValue(`${PASSWORD}-retry`);
  });

  it("translates an expired-link error on language change without submitting again", async () => {
    const fetchMock = mockAcceptance(async () =>
      Response.json(
        {
          code: "invitation_expired",
          message: "Ce lien d’invitation a expiré.",
          fields: {},
        },
        { status: 400 },
      ),
    );
    renderInvitation();
    const user = await fillPasswords();
    await user.click(screen.getByRole("button", { name: SUBMIT }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Ce lien d’invitation a expiré.");

    const languageSwitch = screen.getByRole("button", { name: "English" });
    await user.click(languageSwitch);

    expect(screen.getByRole("alert")).toHaveTextContent(/expired/i);
    expect(screen.getByRole("alert")).not.toHaveTextContent("Ce lien d’invitation a expiré.");
    expect(languageSwitch).toHaveFocus();
    expect(acceptanceCalls(fetchMock)).toHaveLength(1);
  });

  it("clears stale server field text on language change while keeping both passwords", async () => {
    const fetchMock = mockAcceptance(async () =>
      Response.json(
        {
          code: "validation_error",
          message: "Vérifiez les champs indiqués.",
          fields: { password: [PASSWORD_ERROR] },
        },
        { status: 400 },
      ),
    );
    renderInvitation();
    const user = await fillPasswords();
    await user.click(screen.getByRole("button", { name: SUBMIT }));
    expect(await screen.findByText(PASSWORD_ERROR)).toBeVisible();

    await user.click(screen.getByRole("button", { name: "English" }));

    expect(screen.queryByText(PASSWORD_ERROR)).not.toBeInTheDocument();
    expect(screen.getByLabelText(/^Password$/)).toHaveValue(PASSWORD);
    expect(screen.getByLabelText(/^Confirm password$/)).toHaveValue(PASSWORD);
    expect(acceptanceCalls(fetchMock)).toHaveLength(1);
  });

  it("keeps an existing session until the visitor explicitly signs out after acceptance", async () => {
    let signedIn = true;
    const fetchMock = vi.fn(async (input: RequestInfo | URL, options?: RequestInit) => {
      const url = String(input);
      if (url === "/api/me/") {
        return signedIn ? Response.json(testUser("admin")) : new Response(null, { status: 401 });
      }
      if (url === ACCEPT && options?.method === "POST") return Response.json({ accepted: true });
      if (url.endsWith("/auth/session") && options?.method === "DELETE") {
        signedIn = false;
        return new Response(null, { status: 401 });
      }
      return new Response(null, { status: 404 });
    });
    vi.stubGlobal("fetch", fetchMock);
    renderInvitation();
    await screen.findByRole("button", { name: "Déconnexion" });
    const user = await fillPasswords();
    await user.click(screen.getByRole("button", { name: SUBMIT }));

    expect(await within(screen.getByRole("main")).findByRole("status")).toHaveTextContent(
      /compte.*prêt/i,
    );
    expect(screen.getByTestId("current-path")).toHaveTextContent(`/invitation/${TOKEN}`);
    expect(signedIn).toBe(true);
    expect(
      fetchMock.mock.calls.some(
        ([url, options]) => String(url).endsWith("/auth/login") || options?.method === "DELETE",
      ),
    ).toBe(false);

    await user.click(screen.getByRole("button", { name: "Déconnexion" }));

    await waitFor(() => expect(screen.getByTestId("current-path")).toHaveTextContent("/sign-in"));
    expect(await screen.findByRole("heading", { name: "Connexion" })).toBeInTheDocument();
    expect(signedIn).toBe(false);
    expect(acceptanceCalls(fetchMock)).toHaveLength(1);
  });

  it("allows only one pending acceptance request", async () => {
    let resolveResponse!: (response: Response) => void;
    const response = new Promise<Response>((resolve) => {
      resolveResponse = resolve;
    });
    const fetchMock = mockAcceptance(() => response);
    renderInvitation();
    const user = await fillPasswords();
    await user.dblClick(screen.getByRole("button", { name: SUBMIT }));

    expect(acceptanceCalls(fetchMock)).toHaveLength(1);
    await act(async () => {
      resolveResponse(new Response(null, { status: 200 }));
    });
    await waitFor(() => expect(screen.getByTestId("current-path")).toHaveTextContent("/sign-in"));
  });
});
