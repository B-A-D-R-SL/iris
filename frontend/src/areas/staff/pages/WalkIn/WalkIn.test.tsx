// AI contribution: 50% or more AI-generated
import { act, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import App from "../../../../app/App";
import type { Role } from "../../../../shared/auth/roles";
import type { WalkInDraft } from "../../../../features/households/walkInApi";
import i18n from "../../../../shared/i18n";
import { expectNoAxeViolations, renderWithProviders, testUser } from "../../../../test/render";

const ID = "6f1c2c1e-0000-4000-8000-000000000017";

/** A saved draft as the API returns it (generated data only). */
function draft(overrides: Partial<WalkInDraft> = {}): WalkInDraft {
  return {
    id: ID,
    channel: "walk_in",
    status: "draft",
    email: null,
    preferred_language: "fr",
    phone: "+15145550156",
    street_number: "",
    street_name: "",
    unit: "",
    city: "Montréal",
    postal_code: "",
    identity_checked_in_person: true,
    consent_data_processing_at: "2026-11-02T14:05:00Z",
    consent_text_version: "2026-11-v1",
    members: [
      {
        id: "m1",
        first_name: "Nadia",
        last_name: "Démo",
        date_of_birth: "1990-04-12",
        relation: "holder",
      },
    ],
    created_by_email: "sophie@example.org",
    created_at: "2026-11-02T14:05:00Z",
    updated_at: "2026-11-02T14:05:00Z",
    verified_by_email: "sophie@example.org",
    verified_at: "2026-11-02T14:05:00Z",
    ...overrides,
  } as WalkInDraft;
}

type Handler = () => Response;

/** Fakes /api/me/ and the walk-in endpoints. */
function mockApi({
  role = "intake_worker",
  create = () => Response.json(draft(), { status: 201 }),
  update = () => Response.json(draft()),
  read = () => Response.json(draft()),
}: { role?: Role; create?: Handler; update?: Handler; read?: Handler } = {}) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = input instanceof Request ? input.url : String(input);
    const method = init?.method ?? "GET";
    if (url.endsWith("/api/me/")) return Response.json(testUser(role));
    if (url.endsWith("/api/staff/households/") && method === "POST") return create();
    if (url.endsWith(`/api/staff/households/${ID}/`) && method === "PATCH") return update();
    if (url.endsWith(`/api/staff/households/${ID}/`) && method === "GET") return read();
    return new Response(null, { status: 404 });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function sentBody(fetchMock: ReturnType<typeof mockApi>, method: "POST" | "PATCH") {
  const calls = fetchMock.mock.calls.filter(([, init]) => init?.method === method);
  const last = calls.at(-1);
  if (!last) throw new Error(`Nothing was sent with ${method}`);
  return JSON.parse(last[1]?.body as string) as Record<string, unknown>;
}

const sent = (fetchMock: ReturnType<typeof mockApi>, method: string) =>
  fetchMock.mock.calls.some(([, init]) => init?.method === method);

const button = (name: string) => screen.getByRole("button", { name });

async function fillHolder() {
  await userEvent.type(screen.getByLabelText("Prénom"), "Nadia");
  await userEvent.type(screen.getByLabelText("Nom de famille"), "Démo");
  await userEvent.type(screen.getByLabelText("Date de naissance"), "1990-04-12");
  await userEvent.type(screen.getByLabelText("Téléphone"), "5145550156");
}

const checkId = () =>
  userEvent.click(
    screen.getByRole("checkbox", { name: /Pièce d'identité avec photo vérifiée en personne/ }),
  );

const giveConsent = () =>
  userEvent.click(
    screen.getByRole("checkbox", {
      name: /J'accepte que B\.A\.D\.R\. utilise ces renseignements/,
    }),
  );

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date(2026, 10, 2, 9, 0));
});

afterEach(() => {
  vi.useRealTimers();
});

it("Walk-in registration (US-17) refuses a pasted foreign phone without creating a different Canadian contact", async () => {
  const fetchMock = mockApi();
  renderWithProviders(<App />, { route: "/staff/walk-in" });
  await screen.findByRole("heading", { name: "1. Personne responsable" });
  await fillHolder();
  const user = userEvent.setup();
  const input = screen.getByLabelText("Téléphone");
  await user.clear(input);
  await user.click(input);
  await user.paste("+447911123456");
  await user.click(button("Enregistrer le brouillon"));
  expect(input).toHaveValue("+447911123456");
  expect(input).toHaveAttribute("aria-invalid", "true");
  expect(sent(fetchMock, "POST")).toBe(false);
});

it("Walk-in registration (US-17) refuses an overlong pasted postal code without patching a different address", async () => {
  const fetchMock = mockApi();
  renderWithProviders(<App />, { route: `/staff/walk-in/${ID}` });
  await screen.findByRole("heading", { name: "2. Adresse" });
  const user = userEvent.setup();
  await user.type(screen.getByLabelText(/^Numéro civique/), "123");
  await user.type(screen.getByLabelText("Rue"), "rue Exemple");
  const input = screen.getByLabelText("Code postal");
  await user.click(input);
  await user.paste("H2X 1Y45");
  await user.click(button("Continuer"));
  expect(input).toHaveValue("H2X 1Y45");
  expect(input).toHaveAttribute("aria-invalid", "true");
  expect(sent(fetchMock, "PATCH")).toBe(false);
});

it("Walk-in registration (US-17) creates the draft from the holder step and moves to the address", async () => {
  const fetchMock = mockApi();
  renderWithProviders(<App />, { route: "/staff/walk-in" });
  await screen.findByRole("heading", { name: "1. Personne responsable" });

  await fillHolder();
  await checkId();
  await giveConsent();
  await userEvent.click(button("Continuer"));

  await screen.findByRole("heading", { name: "2. Adresse" });
  expect(sentBody(fetchMock, "POST")).toEqual({
    holder: {
      first_name: "Nadia",
      last_name: "Démo",
      date_of_birth: "1990-04-12",
      email: null,
      phone: "+15145550156",
      preferred_language: "fr",
    },
    identity_checked_in_person: true,
    consent_data_processing: true,
    members: [],
  });
  // Who created the file and when, in Montréal time (AC 3).
  expect(screen.getByText(/Créé par sophie@example\.org le 2 novembre 2026/)).toBeVisible();
});

it("Walk-in registration (US-17) shows clear messages and sends nothing while the holder is incomplete", async () => {
  const fetchMock = mockApi();
  renderWithProviders(<App />, { route: "/staff/walk-in" });
  await screen.findByRole("heading", { name: "1. Personne responsable" });

  await userEvent.type(screen.getByLabelText("Date de naissance"), "2010-05-01");
  await userEvent.click(button("Continuer"));

  expect(await screen.findByText("Corrigez 6 champs.")).toBeVisible();
  expect(screen.getByText("La personne responsable doit avoir 18 ans ou plus.")).toBeVisible();
  expect(
    screen.getByText("Vérifiez la pièce d'identité avec photo en personne avant de continuer."),
  ).toBeVisible();
  expect(
    screen.getByText(
      "Lisez l'avis à voix haute et notez le consentement de la personne avant de continuer.",
    ),
  ).toBeVisible();
  expect(sent(fetchMock, "POST")).toBe(false);
});

it("Walk-in registration (US-17) saves a draft before the ID check and consent, and lists what is still to complete", async () => {
  const fetchMock = mockApi({
    create: () =>
      Response.json(
        draft({
          identity_checked_in_person: false,
          consent_data_processing_at: null,
          consent_text_version: "",
        }),
        { status: 201 },
      ),
  });
  renderWithProviders(<App />, { route: "/staff/walk-in" });
  await screen.findByRole("heading", { name: "1. Personne responsable" });

  await fillHolder();
  await userEvent.click(button("Enregistrer le brouillon"));

  expect(await screen.findByRole("heading", { name: "Brouillon enregistré" })).toBeVisible();
  expect(sentBody(fetchMock, "POST")).toMatchObject({
    identity_checked_in_person: false,
    consent_data_processing: false,
  });
  const todo = screen.getByRole("region", { name: "Reste à faire" });
  expect(
    within(todo).getByText("Vérifier la pièce d'identité avec photo en personne"),
  ).toBeVisible();
  expect(within(todo).getByText("Lire l'avis à voix haute et noter le consentement")).toBeVisible();
  expect(within(todo).getByText("Entrer l'adresse")).toBeVisible();

  await userEvent.click(button("Reprendre l'inscription"));
  expect(await screen.findByRole("heading", { name: "1. Personne responsable" })).toBeVisible();
  expect(screen.getByLabelText("Prénom")).toHaveValue("Nadia");
});

it("Walk-in registration (US-17) resumes a saved draft at the first step still missing information", async () => {
  mockApi();
  renderWithProviders(<App />, { route: `/staff/walk-in/${ID}` });

  expect(await screen.findByRole("heading", { name: "2. Adresse" })).toBeVisible();
  expect(screen.getByLabelText("Ville")).toHaveValue("Montréal");
  expect(screen.getByLabelText("Province")).toHaveValue("QC");
  await userEvent.click(button("Retour"));
  expect(screen.getByLabelText("Nom de famille")).toHaveValue("Démo");
});

it("Walk-in registration (US-17) saves the address, then adds a child as person 2", async () => {
  const fetchMock = mockApi();
  renderWithProviders(<App />, { route: `/staff/walk-in/${ID}` });
  await screen.findByRole("heading", { name: "2. Adresse" });

  await userEvent.type(screen.getByLabelText(/^Numéro civique/), "1234A");
  await userEvent.type(screen.getByLabelText("Rue"), "rue Saint-Denis");
  await userEvent.type(screen.getByLabelText("Code postal"), "h2x1y4");
  await userEvent.click(button("Continuer"));

  await screen.findByRole("heading", { name: "3. Membres du foyer" });
  expect(sentBody(fetchMock, "PATCH").address).toEqual({
    street_number: "1234A",
    street_name: "rue Saint-Denis",
    unit: null,
    city: "Montréal",
    province: "QC",
    postal_code: "H2X 1Y4",
  });
  expect(screen.getByText("Nadia Démo est la personne 1 (personne responsable).")).toBeVisible();

  await userEvent.click(button("Ajouter une personne"));
  const person = screen.getByRole("region", { name: "Personne 2" });
  await userEvent.type(within(person).getByLabelText("Prénom"), "Léo");
  await userEvent.type(within(person).getByLabelText("Nom de famille"), "Démo");
  await userEvent.type(within(person).getByLabelText("Date de naissance"), "2017-01-03");
  await userEvent.click(
    within(person).getByRole("combobox", { name: "Lien avec la personne responsable" }),
  );
  await userEvent.click(await screen.findByRole("option", { name: "Enfant" }));
  await userEvent.click(button("Continuer"));

  await screen.findByRole("heading", { name: "4. Vérification" });
  expect(sentBody(fetchMock, "PATCH").members).toEqual([
    { first_name: "Léo", last_name: "Démo", date_of_birth: "2017-01-03", relation: "child" },
  ]);
  expect(screen.getByText("Personnes dans le foyer : 2")).toBeVisible();
});

it("Walk-in registration (US-17) shows the server's message on the field it refused, on that field's step", async () => {
  mockApi({
    update: () =>
      Response.json(
        {
          code: "validation_error",
          message: "Vérifiez les champs indiqués.",
          fields: { "address.postal_code": ["Code postal refusé par le serveur."] },
        },
        { status: 400 },
      ),
  });
  renderWithProviders(<App />, {
    route: `/staff/walk-in/${ID}`,
  });
  await screen.findByRole("heading", { name: "2. Adresse" });
  await userEvent.type(screen.getByLabelText(/^Numéro civique/), "12");
  await userEvent.type(screen.getByLabelText("Rue"), "rue Exemple");
  await userEvent.type(screen.getByLabelText("Code postal"), "H2X 1Y4");
  await userEvent.click(button("Continuer"));

  expect(await screen.findByText("Code postal refusé par le serveur.")).toBeVisible();
  expect(screen.getByRole("heading", { name: "2. Adresse" })).toBeVisible();
});

it("Walk-in registration (US-17) explains when the server cannot be reached", async () => {
  const fetchMock = mockApi();
  renderWithProviders(<App />, { route: "/staff/walk-in" });
  await screen.findByRole("heading", { name: "1. Personne responsable" });
  await fillHolder();
  fetchMock.mockRejectedValueOnce(new TypeError("Failed to fetch"));
  await userEvent.click(button("Enregistrer le brouillon"));

  expect(
    await screen.findByText(
      "Impossible de joindre le serveur. Vérifiez la connexion, puis réessayez.",
    ),
  ).toBeVisible();
});

it("Walk-in registration (US-17) says when a draft cannot be found", async () => {
  mockApi({
    read: () => Response.json({ code: "not_found", message: "", fields: {} }, { status: 404 }),
  });
  renderWithProviders(<App />, { route: `/staff/walk-in/${ID}` });
  expect(
    await screen.findByText("Ce brouillon est introuvable ou ne peut plus être modifié."),
  ).toBeVisible();
});

it.each<Role>(["admin", "intake_worker"])(
  "Walk-in registration (US-17) is open to %s",
  async (role) => {
    mockApi({ role });
    renderWithProviders(<App />, { route: "/staff/walk-in" });
    expect(await screen.findByRole("heading", { name: "1. Personne responsable" })).toBeVisible();
  },
);

it.each<Role>(["beneficiary", "store_staff", "store_manager"])(
  "Walk-in registration (US-17) is refused to %s, who never sees the form",
  async (role) => {
    const fetchMock = mockApi({ role });
    renderWithProviders(<App />, { route: "/staff/walk-in" });
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    await waitFor(() =>
      expect(screen.queryByRole("heading", { name: "Inscription en personne" })).toBeNull(),
    );
    expect(screen.queryByLabelText("Prénom")).toBeNull();
  },
);

it("Walk-in registration (US-17) is available in English", async () => {
  mockApi();
  await act(() => i18n.changeLanguage("en"));
  renderWithProviders(<App />, { route: "/staff/walk-in" });
  expect(await screen.findByRole("heading", { name: "1. Account holder" })).toBeVisible();
  expect(screen.getByLabelText("Email address (optional)")).toBeVisible();
  expect(button("Save draft")).toBeVisible();
});

it("Walk-in registration (US-17) has no accessibility violations", async () => {
  mockApi();
  const { container } = renderWithProviders(<App />, { route: "/staff/walk-in" });
  await screen.findByRole("heading", { name: "1. Personne responsable" });
  await expectNoAxeViolations(container);
});
