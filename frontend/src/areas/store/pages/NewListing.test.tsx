// AI contribution: 50% or more AI-generated
// File length exception (500 lines): posting, safety refusals and failure logs
// share one endpoint dispatcher plus routed-form, category and date helpers.
// Keeping the three groups beside those fixtures makes their UI/HTTP contracts
// use the same setup when fields, category responses or request payloads change.
import { act, fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "../../../app/App";
import i18n from "../../../shared/i18n";
import { expectNoAxeViolations, renderWithProviders, testUser } from "../../../test/render";

const CATEGORIES = [
  {
    code: "bakery",
    name_fr: "Boulangerie",
    name_en: "Bakery",
    is_food: true,
    default_value_cents: 400,
  },
  {
    code: "hygiene",
    name_fr: "Hygiène personnelle",
    name_en: "Personal hygiene",
    is_food: false,
    default_value_cents: 300,
  },
];

const published = () => Response.json({ id: "1", title: "Pains de la veille" }, { status: 201 });

/** Fakes /api/me/ (a store worker), the posting categories and the posting endpoint. */
function mockApi({
  post = published,
  categories = () => Response.json(CATEGORIES),
}: { post?: () => Response; categories?: () => Response } = {}) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = input instanceof Request ? input.url : String(input);
    if (url.endsWith("/api/me/")) return Response.json(testUser("store_staff"));
    if (url.endsWith("/api/store/listings/categories/")) return categories();
    if (url.endsWith("/api/store/listings/") && init?.method === "POST") return post();
    return new Response(null, { status: 404 });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

/** The JSON body of the posting request. */
function postedBody(fetchMock: ReturnType<typeof mockApi>) {
  const call = fetchMock.mock.calls.find(([, init]) => init?.method === "POST");
  if (!call) throw new Error("Nothing was posted");
  return JSON.parse(call[1]?.body as string) as Record<string, unknown>;
}

const wasPosted = (fetchMock: ReturnType<typeof mockApi>) =>
  fetchMock.mock.calls.some(([, init]) => init?.method === "POST");

async function renderForm() {
  const view = renderWithProviders(<App />, { route: "/store/listings/new" });
  await screen.findByRole("button", { name: "Publier l'offre" });
  return view;
}

async function chooseCategory(name: string) {
  await userEvent.click(screen.getByRole("button", { name: "Catégorie" }));
  const sheet = await screen.findByRole("dialog", { name: "Catégorie" });
  await userEvent.click(within(sheet).getByRole("radio", { name }));
  await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
}

async function fillRequiredFields() {
  await userEvent.type(screen.getByLabelText("Titre"), "Pains de la veille");
  await chooseCategory("Hygiène personnelle");
  await userEvent.click(
    screen.getByRole("checkbox", {
      name: "Je confirme que ces produits sont sécuritaires et permis",
    }),
  );
}

const publish = () => userEvent.click(screen.getByRole("button", { name: "Publier l'offre" }));

beforeEach(() => {
  // Thursday 12 November 2026, 09:00 local: today's 16:00 pickup is still ahead.
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date(2026, 10, 12, 9, 0));
});

afterEach(() => {
  vi.useRealTimers();
});

describe("Post a listing (US-33)", () => {
  it("opens with the defaults: today 16:00 to 18:00, quantity 1, item, 1 per household", async () => {
    mockApi();
    const { container } = await renderForm();

    expect(screen.getByRole("heading", { name: "Publier une offre", level: 1 })).toBeVisible();
    expect(screen.getByLabelText("Quantité")).toHaveValue("1");
    expect(screen.getByLabelText("Maximum par foyer")).toHaveValue("1");
    expect(screen.getByRole("radio", { name: "Article" })).toBeChecked();
    expect(screen.getByRole("radio", { name: "Aujourd'hui" })).toBeChecked();
    expect(screen.getByLabelText("Début")).toHaveValue("16:00");
    expect(screen.getByLabelText("Fin")).toHaveValue("18:00");
    expect(screen.getByText("L'adresse de votre commerce")).toBeVisible();
    // Best before only appears once a food category is chosen.
    expect(screen.queryByLabelText("Meilleur avant")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Publier" })).toHaveAttribute("aria-current", "page");
    await expectNoAxeViolations(container);
  });

  it("publishes a listing and gets ready for the next one", async () => {
    const fetchMock = mockApi();
    await renderForm();
    await fillRequiredFields();
    await publish();

    expect(await screen.findByText("Offre publiée")).toBeVisible();
    expect(screen.getByText("« Pains de la veille » est maintenant publiée.")).toBeVisible();
    const body = postedBody(fetchMock);
    expect(body).toMatchObject({
      category: "hygiene",
      title: "Pains de la veille",
      quantity: 1,
      unit: "item",
      max_per_household: 1,
      best_before: null,
      safe_and_allowed: true,
    });
    expect(new Date(body.pickup_start as string).getTime()).toBe(
      new Date(2026, 10, 12, 16).getTime(),
    );
    expect(new Date(body.pickup_end as string).getTime()).toBe(
      new Date(2026, 10, 12, 18).getTime(),
    );
    // Back to the defaults for the next listing.
    expect(screen.getByLabelText("Titre")).toHaveValue("");
    expect(screen.getByRole("button", { name: "Catégorie" })).toHaveTextContent(
      "Choisir une catégorie",
    );
  });

  it("asks for a best-before date for food and sends the chosen values", async () => {
    const fetchMock = mockApi();
    await renderForm();
    await userEvent.type(screen.getByLabelText("Titre"), "Pains de la veille");
    await chooseCategory("Boulangerie");
    await userEvent.click(screen.getByRole("radio", { name: "Demain" }));
    await userEvent.click(screen.getByRole("button", { name: "Augmenter (Quantité)" }));
    await userEvent.click(screen.getByRole("button", { name: "Augmenter (Quantité)" }));
    await userEvent.click(screen.getByRole("radio", { name: "Lot" }));
    await userEvent.type(screen.getByLabelText("Meilleur avant"), "2026-11-14");
    await userEvent.click(screen.getByRole("checkbox", { name: /sécuritaires et permis/ }));
    await publish();

    await screen.findByText("Offre publiée");
    expect(postedBody(fetchMock)).toMatchObject({
      category: "bakery",
      quantity: 3,
      unit: "bundle",
      best_before: "2026-11-14",
      pickup_start: expect.stringMatching(/^2026-11-13T16:00:00/),
    });
  });

  it("lists every field to fix before sending anything", async () => {
    const fetchMock = mockApi();
    const { container } = await renderForm();
    await publish();

    expect(await screen.findByText("Vérifiez 3 champs")).toBeVisible();
    expect(screen.getByText("Remplissez ce champ.")).toBeVisible();
    expect(screen.getByText("Choisissez une catégorie.")).toBeVisible();
    expect(screen.getByText("Cochez cette case pour publier.")).toBeVisible();
    expect(wasPosted(fetchMock)).toBe(false);
    await expectNoAxeViolations(container);
  });

  it("sends formatted dates to the API and shows its pickup and safety refusals", async () => {
    const fetchMock = mockApi({
      post: () =>
        Response.json(
          {
            code: "validation_error",
            message: "Vérifiez les champs indiqués.",
            fields: {
              pickup_end: ["Durée refusée par le serveur."],
              best_before: ["Date refusée par le serveur."],
            },
          },
          { status: 400 },
        ),
    });
    await renderForm();
    await fillRequiredFields();
    await chooseCategory("Boulangerie");
    fireEvent.change(screen.getByLabelText("Fin"), { target: { value: "16:15" } });
    await userEvent.type(screen.getByLabelText("Meilleur avant"), "2026-11-11");
    await publish();

    expect(await screen.findByText("Vérifiez 2 champs")).toBeVisible();
    expect(screen.getByText("Durée refusée par le serveur.")).toBeVisible();
    expect(screen.getByText("Date refusée par le serveur.")).toBeVisible();
    expect(postedBody(fetchMock)).toMatchObject({
      pickup_end: expect.stringMatching(/T16:15:00/),
      best_before: "2026-11-11",
    });
  });

  it("does not clamp the steppers to hard-coded posting limits", async () => {
    mockApi();
    await renderForm();
    const decrease = screen.getByRole("button", { name: "Diminuer (Maximum par foyer)" });
    const increase = screen.getByRole("button", { name: "Augmenter (Maximum par foyer)" });
    expect(decrease).toBeEnabled();
    for (let click = 0; click < 9; click += 1) await userEvent.click(increase);
    expect(screen.getByLabelText("Maximum par foyer")).toHaveValue("10");
    expect(increase).toBeEnabled();
    await userEvent.click(increase);
    expect(screen.getByLabelText("Maximum par foyer")).toHaveValue("11");
  });

  it("sends values beyond default limits and displays the API's field errors", async () => {
    const fetchMock = mockApi({
      post: () =>
        Response.json(
          {
            code: "validation_error",
            message: "Vérifiez les champs indiqués.",
            fields: { quantity: ["Quantité refusée par le serveur."] },
          },
          { status: 400 },
        ),
    });
    await renderForm();
    await fillRequiredFields();
    fireEvent.change(screen.getByLabelText("Titre"), { target: { value: "x".repeat(81) } });
    fireEvent.change(screen.getByLabelText(/^Description/), { target: { value: "x".repeat(501) } });
    const quantity = screen.getByLabelText("Quantité");
    await userEvent.clear(quantity);
    await userEvent.type(quantity, "1000");
    await publish();

    expect(await screen.findByText("Quantité refusée par le serveur.")).toBeVisible();
    expect(postedBody(fetchMock)).toMatchObject({
      title: "x".repeat(81),
      description: "x".repeat(501),
      quantity: 1000,
    });
  });

  it("shows the server's message under the field it refused", async () => {
    mockApi({
      post: () =>
        Response.json(
          {
            code: "validation_error",
            message: "Vérifiez les champs indiqués.",
            fields: { pickup_start: ["Choisissez un début entre maintenant et 3 jours."] },
          },
          { status: 400 },
        ),
    });
    await renderForm();
    await fillRequiredFields();
    await publish();

    expect(
      await screen.findByText("Choisissez un début entre maintenant et 3 jours."),
    ).toBeVisible();
    expect(screen.getByText("Vérifiez 1 champ")).toBeVisible();
    // Nothing is lost: the worker fixes the field and publishes again.
    expect(screen.getByLabelText("Titre")).toHaveValue("Pains de la veille");
  });

  it("explains a refusal that no field can fix", async () => {
    mockApi({
      post: () =>
        Response.json(
          {
            code: "posting_unavailable",
            message: "Les vérifications de sécurité ne sont pas encore disponibles.",
            fields: {},
          },
          { status: 503 },
        ),
    });
    await renderForm();
    await fillRequiredFields();
    await publish();

    const notice = await screen.findByRole("alert");
    expect(notice).toHaveTextContent("L'offre n'a pas été publiée");
    expect(notice).toHaveTextContent(
      "Les vérifications de sécurité ne sont pas encore disponibles.",
    );
  });

  it("still explains a 400 that names no field", async () => {
    mockApi({
      post: () =>
        Response.json(
          { code: "validation_error", message: "Vérifiez les champs indiqués.", fields: {} },
          { status: 400 },
        ),
    });
    await renderForm();
    await fillRequiredFields();
    await publish();

    const notice = await screen.findByRole("alert");
    expect(notice).toHaveTextContent("L'offre n'a pas été publiée");
    expect(notice).toHaveTextContent("Vérifiez les champs indiqués.");
  });

  it("asks to try again after a 400 with no message at all", async () => {
    mockApi({ post: () => new Response("Bad Request", { status: 400 }) });
    await renderForm();
    await fillRequiredFields();
    await publish();

    const notice = await screen.findByRole("alert");
    expect(notice).toHaveTextContent("L'offre n'a pas été publiée");
    expect(notice).toHaveTextContent("Réessayez dans quelques minutes.");
  });

  it("asks to retry when the categories cannot be loaded", async () => {
    mockApi({ categories: () => new Response(null, { status: 503 }) });
    renderWithProviders(<App />, { route: "/store/listings/new" });

    expect(await screen.findByText("Impossible d'afficher cette page")).toBeVisible();
    expect(screen.getByRole("button", { name: "Réessayer" })).toBeVisible();
    expect(screen.queryByRole("button", { name: "Publier l'offre" })).not.toBeInTheDocument();
  });

  it("works in English and asks the server for English messages", async () => {
    const fetchMock = mockApi();
    await renderForm();
    await act(async () => {
      await i18n.changeLanguage("en");
    });

    await userEvent.type(screen.getByLabelText("Title"), "Day-old bread");
    await userEvent.click(screen.getByRole("button", { name: "Category" }));
    const sheet = await screen.findByRole("dialog", { name: "Category" });
    expect(within(sheet).getByRole("radiogroup", { name: "Food" })).toBeVisible();
    await userEvent.click(within(sheet).getByRole("radio", { name: "Personal hygiene" }));
    await userEvent.click(screen.getByRole("checkbox", { name: /safe and allowed/ }));
    await userEvent.click(screen.getByRole("button", { name: "Publish the listing" }));

    expect(await screen.findByText("Listing published")).toBeVisible();
    const call = fetchMock.mock.calls.find(([, init]) => init?.method === "POST");
    expect(call?.[1]?.headers).toMatchObject({ "Accept-Language": "en" });
  });
});

/** A 400 from the posting endpoint with these field messages. */
const refused = (fields: Record<string, string[]>) => () =>
  Response.json(
    { code: "validation_error", message: "Vérifiez les champs indiqués.", fields },
    { status: 400 },
  );

// Suite size exception: this callback registers independent safety cases under
// one French-locale reset, reusing the posting helpers to verify category lists,
// field refusals and the English switch against the same form/API contract.
describe("Listing safety checks (US-34)", () => {
  beforeEach(async () => {
    await act(async () => {
      await i18n.changeLanguage("fr");
    });
  });

  it("offers only the categories the server allows, so prohibited ones cannot be chosen", async () => {
    // The server left out a prohibited category: only bakery comes back.
    const fetchMock = mockApi({ categories: () => Response.json([CATEGORIES[0]]) });
    await renderForm();
    await userEvent.click(screen.getByRole("button", { name: "Catégorie" }));
    const sheet = await screen.findByRole("dialog", { name: "Catégorie" });

    expect(within(sheet).getByRole("radio", { name: "Boulangerie" })).toBeVisible();
    expect(within(sheet).queryByRole("radio", { name: "Hygiène personnelle" })).toBeNull();
    const urls = fetchMock.mock.calls.map(([input]) => String(input));
    expect(urls).toContain("/api/store/listings/categories/");
    expect(urls).not.toContain("/api/categories/");
  });

  // Full form interactions (plus axe in French) can exceed the 5s default on VMs.
  it("shows each safety refusal under its field, in French", async () => {
    mockApi({
      post: refused({
        category: ["Cette catégorie ne peut pas être publiée. Choisissez-en une autre."],
        best_before: ["Choisissez le 12 nov. 2026 ou après (fin de la cueillette)."],
        safe_and_allowed: ["Cochez cette case pour publier."],
      }),
    });
    const { container } = await renderForm();
    await fillRequiredFields();
    await chooseCategory("Boulangerie");
    await userEvent.type(screen.getByLabelText("Meilleur avant"), "2026-11-11");
    await publish();

    expect(await screen.findByText("Vérifiez 3 champs")).toBeVisible();
    const category = screen.getByRole("button", { name: "Catégorie" });
    expect(category).toHaveAccessibleDescription(
      "Cette catégorie ne peut pas être publiée. Choisissez-en une autre.",
    );
    expect(screen.getByLabelText("Meilleur avant")).toHaveAccessibleDescription(
      expect.stringContaining("Choisissez le 12 nov. 2026 ou après (fin de la cueillette)."),
    );
    expect(screen.getByText("Cochez cette case pour publier.")).toBeVisible();
    await expectNoAxeViolations(container);
  }, 15000);

  it("shows the server's English safety messages after switching language", async () => {
    const fetchMock = mockApi({
      post: refused({
        best_before: ["Enter a best-before date. It is required for food."],
      }),
    });
    await renderForm();
    await act(async () => {
      await i18n.changeLanguage("en");
    });
    await userEvent.type(screen.getByLabelText("Title"), "Day-old bread");
    await userEvent.click(screen.getByRole("button", { name: "Category" }));
    const sheet = await screen.findByRole("dialog", { name: "Category" });
    await userEvent.click(within(sheet).getByRole("radio", { name: "Bakery" }));
    await userEvent.type(screen.getByLabelText("Best before"), "2026-11-14");
    await userEvent.click(screen.getByRole("checkbox", { name: /safe and allowed/ }));
    await userEvent.click(screen.getByRole("button", { name: "Publish the listing" }));

    expect(
      await screen.findByText("Enter a best-before date. It is required for food."),
    ).toBeVisible();
    const call = fetchMock.mock.calls.find(([, init]) => init?.method === "POST");
    expect(call?.[1]?.headers).toMatchObject({ "Accept-Language": "en" });
  }, 15000);

  it("shows the prohibited-items links as unavailable placeholders", async () => {
    mockApi();
    await renderForm();
    const link = screen.getByRole("button", { name: "Voir la liste des produits interdits" });
    expect(link).toHaveAttribute("aria-disabled", "true");
    await userEvent.click(link);
    // Nothing opens and the worker stays on the form.
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Publier l'offre" })).toBeVisible();

    await userEvent.click(screen.getByRole("button", { name: "Catégorie" }));
    const sheet = await screen.findByRole("dialog", { name: "Catégorie" });
    expect(within(sheet).getByRole("button", { name: "Voir la liste" })).toHaveAttribute(
      "aria-disabled",
      "true",
    );

    await act(async () => {
      await i18n.changeLanguage("en");
    });
    expect(screen.getByRole("button", { name: "See the list of prohibited items" })).toBeVisible();
  });
});

describe("Failed post log (FIX-12)", () => {
  /** The JSON entries the shared logger wrote to one console channel. */
  const entries = (spy: { mock: { calls: unknown[][] } }) =>
    spy.mock.calls.map(([line]) => JSON.parse(String(line)) as Record<string, unknown>);

  afterEach(() => vi.restoreAllMocks());

  it("logs a server failure as an error with its status code only", async () => {
    const error = vi.spyOn(console, "error").mockImplementation(() => {});
    mockApi({
      post: () =>
        Response.json(
          { code: "posting_unavailable", message: "Indisponible.", fields: {} },
          { status: 503 },
        ),
    });
    await renderForm();
    await fillRequiredFields();
    await publish();
    await screen.findByText("L'offre n'a pas été publiée");

    expect(entries(error)).toEqual([
      {
        timestamp: expect.any(String),
        level: "ERROR",
        event: "listing_post_failed",
        status_code: 503,
      },
    ]);
  });

  it("logs a refused post as a warning, without anything the worker typed", async () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    mockApi({
      post: () =>
        Response.json(
          { code: "validation_error", message: "Vérifiez.", fields: { title: ["Refusé."] } },
          { status: 400 },
        ),
    });
    await renderForm();
    await fillRequiredFields();
    await publish();
    await screen.findByText("Refusé.");

    expect(entries(warn)).toEqual([
      {
        timestamp: expect.any(String),
        level: "WARNING",
        event: "listing_post_failed",
        status_code: 400,
      },
    ]);
    expect(JSON.stringify(warn.mock.calls)).not.toContain("Pains de la veille");
  });

  it("logs a 201 whose answer cannot be read as an error with its status code", async () => {
    const error = vi.spyOn(console, "error").mockImplementation(() => {});
    mockApi({ post: () => new Response("{not json", { status: 201 }) });
    await renderForm();
    await fillRequiredFields();
    await publish();
    await screen.findByRole("alert");

    expect(entries(error)).toEqual([
      {
        timestamp: expect.any(String),
        level: "ERROR",
        event: "listing_post_failed",
        status_code: 201,
      },
    ]);
  });

  it("logs a lost connection as an error with no status code", async () => {
    const error = vi.spyOn(console, "error").mockImplementation(() => {});
    const fetchMock = mockApi();
    const answer = fetchMock.getMockImplementation()!;
    fetchMock.mockImplementation(async (input, init) => {
      if (init?.method === "POST") throw new TypeError("Failed to fetch");
      return answer(input, init);
    });
    await renderForm();
    await fillRequiredFields();
    await publish();
    await screen.findByText("Vérifiez votre connexion Internet, puis réessayez.");

    expect(entries(error)).toEqual([
      {
        timestamp: expect.any(String),
        level: "ERROR",
        event: "listing_post_failed",
        status_code: null,
      },
    ]);
  });
});
