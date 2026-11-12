// AI contribution: 50% or more AI-generated
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "../../../app/App";
import i18n from "../../../shared/i18n";
import { renderWithProviders, testUser } from "../../../test/render";
import { PartnerApplications } from "./PartnerApplications";

const application = {
  id: "00000000-0000-4000-8000-000000000001",
  status: "submitted",
  business_name: "Bakery",
  business_type: "grocery",
  city: "Montreal",
  contact_email: "owner@example.com",
  contact_first_name: "Marie",
  contact_last_name: "Test",
  contact_phone: "+15145550123",
  contact_role: "Owner",
  created_at: "2026-11-01T12:00:00Z",
  decided_at: null,
  decision_reason: null,
  expected_frequency: "weekly",
  goods_categories: ["bakery"],
  language: "fr",
  message: "Fresh bread",
  neq: null,
  opening_hours: "9-5",
  postal_code: "H2X 1Y4",
  street_name: "Main",
  street_number: "12",
  unit: null,
  website: null,
};
const list = (
  results = [application],
  next: string | null = null,
  previous: string | null = null,
) => Response.json({ count: results.length, results, next, previous });
afterEach(async () => {
  document.cookie = "csrftoken=; Max-Age=0; Path=/";
  document.cookie = "django_language=; Max-Age=0; Path=/";
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  await i18n.changeLanguage("fr");
});

describe("Partner applications", () => {
  it("filters, pages, and shows application details", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) =>
      list(
        [application],
        String(input).includes("page=2") ? null : "next",
        String(input).includes("page=2") ? "previous" : null,
      ),
    );
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    renderWithProviders(<PartnerApplications />);
    await screen.findByRole("button", { name: "Voir Bakery" });
    await user.click(screen.getByRole("button", { name: "Suivant" }));
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("page=2"), expect.anything()),
    );
    await user.click(screen.getByRole("combobox", { name: "Filtrer par statut" }));
    await user.click(screen.getByRole("option", { name: "Soumise" }));
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("page=1&status=submitted"),
        expect.anything(),
      ),
    );
    await user.click(await screen.findByRole("button", { name: "Voir Bakery" }));
    expect(await screen.findByText("Fresh bread")).toBeInTheDocument();
    expect(screen.getByText("Marie Test")).toBeInTheDocument();
    expect(screen.getByText("Épicerie")).toBeInTheDocument();
    expect(screen.getByText("Chaque semaine")).toBeInTheDocument();
  });
  it("returns to the first page after a decision on a later page", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) =>
      init?.method === "POST"
        ? Response.json({ ...application, status: "approved" })
        : list(
            [application],
            String(input).includes("page=2") ? null : "next",
            String(input).includes("page=2") ? "previous" : null,
          ),
    );
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    renderWithProviders(<PartnerApplications />);
    await user.click(await screen.findByRole("button", { name: "Suivant" }));
    await waitFor(() => expect(screen.getByText("Page 2")).toBeInTheDocument());
    await user.click(await screen.findByRole("button", { name: "Voir Bakery" }));
    await user.click(screen.getByRole("button", { name: "Approuver" }));
    const dialog = await screen.findByRole("dialog", { name: "Confirmer l’approbation" });
    await user.click(within(dialog).getByRole("button", { name: "Approuver" }));
    expect(await screen.findByText("Page 1")).toBeInTheDocument();
  });
  it("confirms approval and sends CSRF token", async () => {
    document.cookie = "csrftoken=test-token";
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) =>
      init?.method === "POST" ? Response.json({ ...application, status: "approved" }) : list(),
    );
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    renderWithProviders(<PartnerApplications />);
    await user.click(await screen.findByRole("button", { name: "Voir Bakery" }));
    await user.click(screen.getByRole("button", { name: "Approuver" }));
    const dialog = await screen.findByRole("dialog", { name: "Confirmer l’approbation" });
    expect(fetchMock.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(0);
    await user.click(within(dialog).getByRole("button", { name: "Approuver" }));
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining(`${application.id}/approve/`),
        expect.objectContaining({
          method: "POST",
          headers: expect.objectContaining({ "X-CSRFToken": "test-token" }),
        }),
      ),
    );
    expect(await screen.findByText("Décision enregistrée")).toBeInTheDocument();
  });
  it("requires a rejection reason, submits it trimmed, and reports failure", async () => {
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) =>
      init?.method === "POST" ? new Response(null, { status: 409 }) : list(),
    );
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    renderWithProviders(<PartnerApplications />);
    await user.click(await screen.findByRole("button", { name: "Voir Bakery" }));
    await user.click(screen.getByRole("button", { name: "Refuser" }));
    const dialog = await screen.findByRole("dialog", { name: "Confirmer le refus" });
    await user.click(within(dialog).getByRole("button", { name: "Refuser" }));
    expect(
      within(dialog).getByText("Entrez un motif de 500 caractères au maximum."),
    ).toBeInTheDocument();
    await user.type(within(dialog).getByLabelText(/Motif/), "  Outside area  ");
    await user.click(within(dialog).getByRole("button", { name: "Refuser" }));
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/reject/"),
        expect.objectContaining({ body: JSON.stringify({ reason: "Outside area" }) }),
      ),
    );
    expect(await screen.findByText("La décision n’a pas été enregistrée")).toBeInTheDocument();
  });
  it("renders English and disallows decisions for decided applications", async () => {
    await i18n.changeLanguage("en");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(list([{ ...application, status: "approved" }])),
    );
    const user = userEvent.setup();
    renderWithProviders(<PartnerApplications />);
    await user.click(await screen.findByRole("button", { name: "View Bakery" }));
    expect(screen.getByText("Business type")).toBeInTheDocument();
    expect(screen.getByText("Grocery")).toBeInTheDocument();
    expect(screen.getByText("Weekly")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Approve" })).not.toBeInTheDocument();
  });
  it.each([
    [
      "en",
      "An account already uses this email address.",
      "View Bakery",
      "Approve",
      "Confirm approval",
    ],
    [
      "fr",
      "Un compte utilise déjà ce courriel.",
      "Voir Bakery",
      "Approuver",
      "Confirmer l’approbation",
    ],
  ])(
    "shows the actual registered-email refusal in %s",
    async (language, message, view, approve, title) => {
      await i18n.changeLanguage(language);
      document.cookie = `django_language=${language === "en" ? "fr" : "en"}; Path=/`;
      const fetchMock = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) =>
        init?.method === "POST"
          ? Response.json(
              {
                code: "validation_error",
                message: "Check the highlighted fields.",
                fields: { non_field_errors: [message] },
              },
              { status: 400 },
            )
          : list(),
      );
      vi.stubGlobal("fetch", fetchMock);
      const user = userEvent.setup();
      renderWithProviders(<PartnerApplications />);
      await user.click(await screen.findByRole("button", { name: view }));
      await user.click(screen.getByRole("button", { name: approve }));
      const dialog = await screen.findByRole("dialog", { name: title });
      await user.click(within(dialog).getByRole("button", { name: approve }));
      expect(await screen.findByText(message)).toBeInTheDocument();
      expect(
        screen.queryByText(/may already have been decided|peut-être déjà été prise/),
      ).not.toBeInTheDocument();
      expect(document.cookie).toContain(`django_language=${language}`);
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/approve/"),
        expect.objectContaining({
          headers: expect.objectContaining({ "Accept-Language": language }),
        }),
      );
      expect(screen.queryByText("Check the highlighted fields.")).not.toBeInTheDocument();
    },
  );
  it.each([
    [
      "public refusal",
      () =>
        Response.json(
          {
            code: "permission_denied",
            message: "Only admins can review partner applications.",
            fields: {},
          },
          { status: 403 },
        ),
      "Only admins can review partner applications.",
    ],
    [
      "conflict",
      () => new Response(null, { status: 409 }),
      "This application has already been approved or rejected. Refresh the list.",
    ],
    [
      "server failure",
      () =>
        Response.json(
          { code: "error", message: "Internal configuration secret", fields: {} },
          { status: 500 },
        ),
      "Try again later. If the problem continues, contact an administrator.",
    ],
    [
      "invalid JSON",
      () => new Response("<html>Internal configuration secret</html>", { status: 400 }),
      "Try again later. If the problem continues, contact an administrator.",
    ],
    [
      "malformed fields",
      () =>
        Response.json(
          { code: "validation_error", message: "Check the highlighted fields.", fields: [] },
          { status: 400 },
        ),
      "Try again later. If the problem continues, contact an administrator.",
    ],
    [
      "network failure",
      () => {
        throw new TypeError("Internal configuration secret");
      },
      "Try again later. If the problem continues, contact an administrator.",
    ],
  ])("handles %s without exposing internal response text", async (_label, response, expected) => {
    const warning = vi.spyOn(console, "warn").mockImplementation(() => {});
    const error = vi.spyOn(console, "error").mockImplementation(() => {});
    await i18n.changeLanguage("en");
    vi.stubGlobal(
      "fetch",
      vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) =>
        init?.method === "POST" ? response() : list(),
      ),
    );
    const user = userEvent.setup();
    renderWithProviders(<PartnerApplications />);
    await user.click(await screen.findByRole("button", { name: "View Bakery" }));
    await user.click(screen.getByRole("button", { name: "Approve" }));
    const dialog = await screen.findByRole("dialog", { name: "Confirm approval" });
    await user.click(within(dialog).getByRole("button", { name: "Approve" }));
    expect(await screen.findByText(expected)).toBeInTheDocument();
    expect(screen.queryByText(/Internal configuration secret/)).not.toBeInTheDocument();
    expect(JSON.stringify([...warning.mock.calls, ...error.mock.calls])).not.toContain(
      "Internal configuration secret",
    );
  });
  it("protects the route from non-admins", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) =>
      String(input).endsWith("/api/me/")
        ? Response.json(testUser("intake_worker"))
        : new Response(null, { status: 404 }),
    );
    vi.stubGlobal("fetch", fetchMock);
    renderWithProviders(<App />, { route: "/staff/partners" });
    await screen.findByRole("heading", { name: "Foyers" });
    expect(
      fetchMock.mock.calls.some(([url]) =>
        String(url).includes("/api/staff/partner-applications/"),
      ),
    ).toBe(false);
  });
});
