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
    expect(screen.queryByRole("button", { name: "Approve" })).not.toBeInTheDocument();
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
