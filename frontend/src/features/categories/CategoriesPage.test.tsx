/**
 * AI contribution: 50% or more AI-generated
 * Tests for the category management page (US-35, T-05.35.2).
 */

import { act, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import App from "../../app/App";
import type { Role } from "../accounts/currentUser";
import i18n from "../../shared/i18n";
import { expectNoAxeViolations, renderWithProviders, testUser } from "../../test/render";
import type { StaffCategory } from "./adminApi";
import { CategoriesPage } from "./CategoriesPage";

const bakery: StaffCategory = {
  code: "bakery",
  name_fr: "Boulangerie",
  name_en: "Bakery",
  is_food: true,
  default_value_cents: 400,
  is_active: true,
};

const school: StaffCategory = {
  code: "school_supplies",
  name_fr: "Fournitures scolaires",
  name_en: "School supplies",
  is_food: false,
  default_value_cents: 500,
  is_active: false,
};

type Handler = (body: Record<string, unknown>) => Response;

/** Fakes /api/me/ and the admin category endpoints. */
function mockApi({
  role = "admin",
  list = () => Response.json([bakery, school]),
  create = (body) => Response.json(body, { status: 201 }),
  update = (body) => Response.json({ ...bakery, ...body }),
}: {
  role?: Role;
  list?: () => Response;
  create?: Handler;
  update?: Handler;
} = {}) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = input instanceof Request ? input.url : String(input);
    const method = init?.method ?? "GET";
    const body = init?.body ? (JSON.parse(init.body as string) as Record<string, unknown>) : {};
    if (url.endsWith("/api/me/")) return Response.json(testUser(role));
    if (url.endsWith("/api/staff/categories/") && method === "GET") return list();
    if (url.endsWith("/api/staff/categories/") && method === "POST") return create(body);
    if (/\/api\/staff\/categories\/[a-z_]+\/$/.test(url) && method === "PATCH") return update(body);
    return new Response(null, { status: 404 });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function sent(fetchMock: ReturnType<typeof mockApi>, method: string) {
  const call = fetchMock.mock.calls.findLast(([, init]) => init?.method === method);
  if (!call) throw new Error(`Nothing sent with ${method}`);
  return { url: String(call[0]), body: JSON.parse(call[1]?.body as string) as unknown };
}

const button = (name: string | RegExp) => screen.getByRole("button", { name });

describe("CategoriesPage", () => {
  it("lists active and inactive categories in French by default", async () => {
    mockApi();
    renderWithProviders(<CategoriesPage />);

    expect(await screen.findByText("Boulangerie")).toBeInTheDocument();
    expect(screen.getByText("Fournitures scolaires")).toBeInTheDocument();
    expect(screen.getByText("Alimentaire")).toBeInTheDocument();
    expect(screen.getByText("Active")).toBeInTheDocument();
    expect(screen.getByText("Inactive")).toBeInTheDocument();
    expect(button("Désactiver Boulangerie")).toBeVisible();
    expect(button("Réactiver Fournitures scolaires")).toBeVisible();
  });

  it("switches names and labels to English", async () => {
    mockApi();
    renderWithProviders(<CategoriesPage />);
    await screen.findByText("Boulangerie");

    await act(async () => {
      await i18n.changeLanguage("en");
    });

    expect(screen.getByText("Bakery")).toBeInTheDocument();
    expect(screen.getByText("Food")).toBeInTheDocument();
    expect(button("Add a category")).toBeVisible();
  });

  it("displays a loading indicator while fetching", () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => new Promise<Response>(() => {})),
    );
    renderWithProviders(<CategoriesPage />);

    expect(screen.getByRole("status")).toHaveTextContent("Chargement");
  });

  it("displays an empty state when there are no categories", async () => {
    mockApi({ list: () => Response.json([]) });
    renderWithProviders(<CategoriesPage />);

    expect(
      await screen.findByRole("heading", { name: "Aucune catégorie disponible" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("displays an error and supports retry", async () => {
    let requests = 0;
    mockApi({
      list: () => {
        requests += 1;
        return requests === 1 ? new Response(null, { status: 503 }) : Response.json([bakery]);
      },
    });
    renderWithProviders(<CategoriesPage />);

    expect(await screen.findByRole("alert")).toBeInTheDocument();
    await userEvent.click(button("Réessayer"));

    expect(await screen.findByText("Boulangerie")).toBeInTheDocument();
    expect(requests).toBe(2);
  });

  it("adds a category with every field (AC1)", async () => {
    const fetchMock = mockApi();
    renderWithProviders(<CategoriesPage />);
    await screen.findByText("Boulangerie");

    await userEvent.click(button("Ajouter une catégorie"));
    const dialog = await screen.findByRole("dialog", { name: "Ajouter une catégorie" });
    await userEvent.type(within(dialog).getByLabelText("Code"), "pet_food");
    await userEvent.type(
      within(dialog).getByLabelText("Nom en français"),
      "Nourriture pour animaux",
    );
    await userEvent.type(within(dialog).getByLabelText("Nom en anglais"), "Pet food");
    await userEvent.type(within(dialog).getByLabelText(/Valeur par défaut/), "6");
    await userEvent.click(within(dialog).getByRole("button", { name: "Enregistrer" }));

    expect(await screen.findByText("Nourriture pour animaux a été enregistrée.")).toBeVisible();
    expect(sent(fetchMock, "POST").body).toEqual({
      code: "pet_food",
      name_fr: "Nourriture pour animaux",
      name_en: "Pet food",
      is_food: false,
      default_value_cents: 600,
      is_active: true,
    });
  });

  it("checks the code and names before sending", async () => {
    const fetchMock = mockApi();
    renderWithProviders(<CategoriesPage />);
    await screen.findByText("Boulangerie");

    await userEvent.click(button("Ajouter une catégorie"));
    const dialog = await screen.findByRole("dialog");
    await userEvent.type(within(dialog).getByLabelText("Code"), "Pet Food");
    await userEvent.click(within(dialog).getByRole("button", { name: "Enregistrer" }));

    expect(
      await within(dialog).findByText(
        "Utilisez des lettres minuscules, des chiffres et _, en commençant par une lettre.",
      ),
    ).toBeVisible();
    expect(fetchMock.mock.calls.some(([, init]) => init?.method === "POST")).toBe(false);
  });

  it("shows the server's message under the field it refused", async () => {
    mockApi({
      create: () =>
        Response.json(
          {
            code: "validation_error",
            message: "Vérifiez les champs indiqués.",
            fields: { default_value_cents: ["Entrez une valeur de 0 à 100000 cents."] },
          },
          { status: 400 },
        ),
    });
    renderWithProviders(<CategoriesPage />);
    await screen.findByText("Boulangerie");

    await userEvent.click(button("Ajouter une catégorie"));
    const dialog = await screen.findByRole("dialog");
    await userEvent.type(within(dialog).getByLabelText("Code"), "pet_food");
    await userEvent.type(within(dialog).getByLabelText("Nom en français"), "Animaux");
    await userEvent.type(within(dialog).getByLabelText("Nom en anglais"), "Pets");
    await userEvent.type(within(dialog).getByLabelText(/Valeur par défaut/), "2000");
    await userEvent.click(within(dialog).getByRole("button", { name: "Enregistrer" }));

    expect(await within(dialog).findByText("Entrez une valeur de 0 à 100000 cents.")).toBeVisible();
  });

  it("edits a category without changing its code", async () => {
    const fetchMock = mockApi();
    renderWithProviders(<CategoriesPage />);
    await screen.findByText("Boulangerie");

    await userEvent.click(button("Modifier Boulangerie"));
    const dialog = await screen.findByRole("dialog", { name: "Modifier la catégorie" });
    expect(within(dialog).getByLabelText("Code")).toHaveAttribute("readonly");
    const english = within(dialog).getByLabelText("Nom en anglais");
    await userEvent.clear(english);
    await userEvent.type(english, "Bakery and bread");
    await userEvent.click(within(dialog).getByRole("button", { name: "Enregistrer" }));

    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    const request = sent(fetchMock, "PATCH");
    expect(request.url).toMatch(/\/api\/staff\/categories\/bakery\/$/);
    expect(request.body).toEqual({
      name_fr: "Boulangerie",
      name_en: "Bakery and bread",
      is_food: true,
      default_value_cents: 400,
    });
  });

  it("deactivates only after confirmation (AC2: no delete)", async () => {
    const fetchMock = mockApi({ update: (body) => Response.json({ ...bakery, ...body }) });
    renderWithProviders(<CategoriesPage />);
    await screen.findByText("Boulangerie");

    expect(screen.queryByRole("button", { name: /Supprimer/ })).not.toBeInTheDocument();
    await userEvent.click(button("Désactiver Boulangerie"));
    const dialog = await screen.findByRole("dialog", { name: "Désactiver Boulangerie ?" });
    expect(fetchMock.mock.calls.some(([, init]) => init?.method === "PATCH")).toBe(false);

    await userEvent.click(within(dialog).getByRole("button", { name: "Désactiver" }));

    expect(
      await screen.findByText(
        "Boulangerie a été désactivée. Les commerces ne peuvent plus l'utiliser.",
      ),
    ).toBeVisible();
    expect(sent(fetchMock, "PATCH").body).toEqual({ is_active: false });
  });

  it("reactivates an inactive category", async () => {
    const fetchMock = mockApi({ update: (body) => Response.json({ ...school, ...body }) });
    renderWithProviders(<CategoriesPage />);
    await screen.findByText("Fournitures scolaires");

    await userEvent.click(button("Réactiver Fournitures scolaires"));

    expect(await screen.findByText("Fournitures scolaires est de nouveau active.")).toBeVisible();
    const request = sent(fetchMock, "PATCH");
    expect(request.url).toMatch(/\/school_supplies\/$/);
    expect(request.body).toEqual({ is_active: true });
  });

  it("explains when the server cannot be reached", async () => {
    const fetchMock = mockApi();
    renderWithProviders(<CategoriesPage />);
    await screen.findByText("Fournitures scolaires");

    fetchMock.mockRejectedValueOnce(new TypeError("Failed to fetch"));
    await userEvent.click(button("Réactiver Fournitures scolaires"));

    expect(
      await screen.findByText(
        "Impossible de joindre le serveur. Vérifiez la connexion, puis réessayez.",
      ),
    ).toBeVisible();
  });

  it("is open to admins inside the staff area", async () => {
    mockApi();
    renderWithProviders(<App />, { route: "/staff/categories" });

    expect(await screen.findByText("Boulangerie")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Catégories" })).toBeInTheDocument();
  });

  it("is refused to intake workers, who never see the page", async () => {
    const fetchMock = mockApi({ role: "intake_worker" });
    renderWithProviders(<App />, { route: "/staff/categories" });

    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    await waitFor(() =>
      expect(screen.queryByRole("button", { name: "Ajouter une catégorie" })).toBeNull(),
    );
    expect(
      fetchMock.mock.calls.some(([input]) => String(input).includes("/api/staff/categories/")),
    ).toBe(false);
  });

  it("has no accessibility violations", async () => {
    mockApi();
    const { container } = renderWithProviders(<CategoriesPage />);
    await screen.findByText("Boulangerie");

    await expectNoAxeViolations(container);
  });
});
