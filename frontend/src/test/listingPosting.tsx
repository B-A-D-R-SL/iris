// AI contribution: 50% or more AI-generated
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, vi } from "vitest";

import App from "../app/App";
import { renderWithProviders, testUser } from "./render";

export const CATEGORIES = [
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
export function mockApi({
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
export function postedBody(fetchMock: ReturnType<typeof mockApi>) {
  const call = fetchMock.mock.calls.find(([, init]) => init?.method === "POST");
  if (!call) throw new Error("Nothing was posted");
  return JSON.parse(call[1]?.body as string) as Record<string, unknown>;
}

export const wasPosted = (fetchMock: ReturnType<typeof mockApi>) =>
  fetchMock.mock.calls.some(([, init]) => init?.method === "POST");

export async function renderForm() {
  const view = renderWithProviders(<App />, { route: "/store/listings/new" });
  await screen.findByRole("button", { name: "Publier l'offre" });
  return view;
}

export async function chooseCategory(name: string) {
  await userEvent.click(screen.getByRole("button", { name: "Catégorie" }));
  const sheet = await screen.findByRole("dialog", { name: "Catégorie" });
  await userEvent.click(within(sheet).getByRole("radio", { name }));
  await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
}

export async function fillRequiredFields() {
  await userEvent.type(screen.getByLabelText("Titre"), "Pains de la veille");
  await chooseCategory("Hygiène personnelle");
  await userEvent.click(
    screen.getByRole("checkbox", {
      name: "Je confirme que ces produits sont sécuritaires et permis",
    }),
  );
}

export const publish = () =>
  userEvent.click(screen.getByRole("button", { name: "Publier l'offre" }));

/** A 400 from the posting endpoint with these field messages. */
export const refused = (fields: Record<string, string[]>) => () =>
  Response.json(
    { code: "validation_error", message: "Vérifiez les champs indiqués.", fields },
    { status: 400 },
  );

export function setupListingClock() {
  beforeEach(() => {
    // Thursday 12 November 2026, 09:00 local: today's pickup is still ahead.
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date(2026, 10, 12, 9, 0));
  });
  afterEach(() => vi.useRealTimers());
}
