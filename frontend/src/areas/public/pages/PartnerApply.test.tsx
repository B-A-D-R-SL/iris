import { act, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import App from "../../../app/App";
import i18n from "../../../shared/i18n";
import { expectNoAxeViolations, renderWithProviders } from "../../../test/render";
import { PartnerApply } from "./PartnerApply";

const bakery = {
  code: "bakery",
  name_fr: "Boulangerie",
  name_en: "Bakery",
  is_food: true,
  default_value_cents: 400,
};
function mockApi(post: Response = new Response(null, { status: 201 })) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, options?: RequestInit) => {
    const url = String(input);
    if (url.includes("/api/categories/")) return Response.json([bakery]);
    if (url.includes("/api/partner-applications/") && options?.method === "POST") return post;
    return new Response(null, { status: 401 });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}
async function fillForm(user: ReturnType<typeof userEvent.setup>) {
  async function paste(label: string, value: string) {
    await user.click(screen.getByLabelText(label));
    await user.paste(value);
  }
  await paste("Nom de l'entreprise", "Boulangerie Exemple");
  await user.click(screen.getByRole("combobox", { name: "Type d'entreprise" }));
  await user.click(await screen.findByRole("option", { name: "Épicerie" }));
  await paste("Numéro civique", "123");
  await paste("Rue", "rue Exemple");
  await user.type(screen.getByLabelText("Code postal"), "H2X1Y4");
  await paste("Prénom de la personne-ressource", "Camille");
  await paste("Nom de la personne-ressource", "Exemple");
  await paste("Courriel", "partner@example.test");
  await user.type(screen.getByLabelText("Téléphone"), "5145550123");
  const goods = screen.getByRole("group", { name: "Types de produits offerts" });
  await user.click(within(goods).getByLabelText("Boulangerie"));
  await user.click(screen.getByLabelText("Chaque semaine"));
  await paste("Heures d'ouverture", "lun-ven 9-17");
  await user.click(
    screen.getByLabelText("J'accepte que B.A.D.R. communique avec moi au sujet de cette demande"),
  );
}
describe("Partner application", () => {
  it("renders the public page and validates required fields without sending", async () => {
    const fetchMock = mockApi();
    const user = userEvent.setup();
    renderWithProviders(<App />, { route: "/partner/apply" });
    expect(await screen.findByRole("heading", { name: "Devenir partenaire" })).toBeInTheDocument();
    await screen.findByLabelText("Boulangerie");
    await user.click(screen.getByRole("button", { name: "Envoyer ma demande" }));
    expect(await screen.findByText(/Vérifiez \d+ champs/)).toBeInTheDocument();
    expect(screen.getByText("Cochez cette case pour envoyer la demande.")).toBeInTheDocument();
    expect(
      fetchMock.mock.calls.some(([url]) => String(url).includes("/api/partner-applications/")),
    ).toBe(false);
  });
  it("posts the specified fields, formats phone and shows the thank-you screen", async () => {
    const fetchMock = mockApi();
    const user = userEvent.setup();
    renderWithProviders(<PartnerApply />);
    await screen.findByLabelText("Boulangerie");
    await fillForm(user);
    await user.click(screen.getByRole("button", { name: "Envoyer ma demande" }));
    expect(await screen.findByRole("heading", { name: "Demande envoyée" })).toBeInTheDocument();
    expect(screen.getByText(/partner@example.test/)).toBeInTheDocument();
    const post = fetchMock.mock.calls.find(([url]) =>
      String(url).includes("/api/partner-applications/"),
    );
    expect(post).toBeDefined();
    const body = JSON.parse(String(post?.[1]?.body));
    expect(body).toMatchObject({
      business_name: "Boulangerie Exemple",
      business_type: "grocery",
      contact_phone: "+15145550123",
      postal_code: "H2X 1Y4",
      goods_categories: ["bakery"],
      expected_frequency: "weekly",
      consent_contact: true,
    });
    expect(post?.[1]?.headers).toMatchObject({ "Accept-Language": "fr" });
  }, 15000);
  it("keeps entered values and shows field-level server errors", async () => {
    mockApi(
      Response.json(
        {
          code: "validation_error",
          message: "Corrigez",
          fields: { contact_email: ["Courriel déjà utilisé."] },
        },
        { status: 400 },
      ),
    );
    const user = userEvent.setup();
    renderWithProviders(<PartnerApply />);
    await screen.findByLabelText("Boulangerie");
    await fillForm(user);
    await user.click(screen.getByRole("button", { name: "Envoyer ma demande" }));
    expect(await screen.findByText("Courriel déjà utilisé.")).toBeInTheDocument();
    expect(screen.getByLabelText("Courriel")).toHaveValue("partner@example.test");
  }, 15000);
  it("shows the duplicate response and supports English", async () => {
    mockApi(
      Response.json(
        {
          code: "application_already_open",
          message: "An application is already in progress.",
          fields: {},
        },
        { status: 409 },
      ),
    );
    const user = userEvent.setup();
    renderWithProviders(<PartnerApply />);
    await screen.findByLabelText("Boulangerie");
    await fillForm(user);
    await act(async () => {
      await i18n.changeLanguage("en");
    });
    expect(screen.getByRole("heading", { name: "Become a partner" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Send my application" }));
    expect(await screen.findByText("An application is already in progress.")).toBeInTheDocument();
    expect(screen.getByLabelText("Email address")).toHaveValue("partner@example.test");
  }, 15000);
  it("shows a retry option when categories cannot be loaded", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) =>
        String(input).includes("/api/categories/")
          ? new Response(null, { status: 503 })
          : new Response(null, { status: 401 }),
      ),
    );
    renderWithProviders(<PartnerApply />);
    expect(await screen.findByRole("button", { name: "Réessayer" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Envoyer ma demande" })).toBeDisabled();
  });

  it("has no detectable accessibility violations in the public layout", async () => {
    mockApi();
    const { container } = renderWithProviders(<App />, { route: "/partner/apply" });
    await screen.findByLabelText("Boulangerie");
    await expectNoAxeViolations(container);
  });
});
