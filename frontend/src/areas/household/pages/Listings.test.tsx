// AI contribution: 50% or more AI-generated
import { act, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { vi } from "vitest";

import App from "../../../app/App";
import i18n from "../../../shared/i18n";
import { expectNoAxeViolations, renderWithProviders } from "../../../test/render";
import {
  card,
  listingRequests,
  mockBrowseApi,
  NEIGHBOURHOOD_GROCERY,
  notApproved,
  page,
} from "./testListings";

const TWO_CARDS = [
  card(),
  card({
    id: "00000000-0000-4000-8000-000000000102",
    title: "Savons",
    category: "hygiene",
    store: NEIGHBOURHOOD_GROCERY,
    pickup_start: "2026-11-13T15:00:00Z",
    pickup_end: "2026-11-13T17:00:00Z",
    units_left: 1,
    unit: "bundle",
    best_before: null,
    photo_url: "https://storage.example/photo.jpg?sig=abc",
  }),
];

async function renderListings(route = "/listings") {
  const view = renderWithProviders(<App />, { route });
  await screen.findByRole("heading", { name: "Offres", level: 1 });
  return view;
}

const cardTitles = () =>
  screen.getAllByRole("heading", { level: 2 }).map((heading) => heading.textContent);

beforeEach(() => {
  // Thursday 12 November 2026, 09:00 in Montreal.
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date("2026-11-12T14:00:00Z"));
});

afterEach(() => {
  vi.useRealTimers();
});

describe("Browse listings (US-36)", () => {
  it("shows each visible listing as a card, in the API's pickup order", async () => {
    mockBrowseApi(() => page(TWO_CARDS));
    const { container } = await renderListings();

    expect(await screen.findByText("2 offres · par heure de cueillette")).toBeVisible();
    expect(cardTitles()).toEqual(["Pains de la veille", "Savons"]);

    const bread = screen.getByRole("link", { name: /Pains de la veille/ });
    expect(bread).toHaveAttribute("href", "/listings/00000000-0000-4000-8000-000000000101");
    expect(within(bread).getByText("Boulangerie du Coin")).toBeVisible();
    expect(within(bread).getByText("Aujourd'hui · 16 h – 18 h")).toBeVisible();
    expect(within(bread).getByText("7 restants")).toBeVisible();
    expect(within(bread).getByText("Meilleur avant 13 nov.")).toBeVisible();

    const soap = screen.getByRole("link", { name: /Savons/ });
    expect(within(soap).getByText("Demain · 10 h – 12 h")).toBeVisible();
    expect(within(soap).getByText("1 lot restant")).toBeVisible();
    expect(within(soap).queryByText(/Meilleur avant/)).not.toBeInTheDocument();
    const photo = soap.querySelector("img");
    expect(photo).toHaveAttribute("src", "https://storage.example/photo.jpg?sig=abc");
    expect(photo).toHaveAttribute("referrerpolicy", "no-referrer");

    await expectNoAxeViolations(container);
  });

  it("filters to listings that can still be picked up today", async () => {
    const fetchMock = mockBrowseApi(() => page(TWO_CARDS));
    await renderListings();
    await screen.findByText("2 offres · par heure de cueillette");

    const today = screen.getByRole("button", { name: "Aujourd'hui" });
    expect(today).toHaveAttribute("aria-pressed", "false");
    await userEvent.click(today);

    await waitFor(() => expect(listingRequests(fetchMock)).toContain("/api/listings/?today=true"));
    expect(screen.getByRole("button", { name: "Aujourd'hui" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  it("filters by category from the bottom sheet", async () => {
    const fetchMock = mockBrowseApi(() => page(TWO_CARDS));
    await renderListings();
    await screen.findByText("2 offres · par heure de cueillette");

    await userEvent.click(screen.getByRole("button", { name: "Catégorie" }));
    const sheet = await screen.findByRole("dialog", { name: "Catégorie" });
    expect(within(sheet).getByRole("radio", { name: "Toutes les catégories" })).toBeChecked();
    expect(within(sheet).getByRole("radiogroup", { name: "Aliments" })).toBeVisible();
    await userEvent.click(within(sheet).getByRole("radio", { name: "Boulangerie" }));

    await waitFor(() =>
      expect(listingRequests(fetchMock)).toContain("/api/listings/?category=bakery"),
    );
    expect(screen.getByRole("button", { name: "Boulangerie" })).toBeVisible();
  });

  it("offers the stores of the loaded listings, and keeps them once one is chosen", async () => {
    const fetchMock = mockBrowseApi((url) =>
      page(url.searchParams.has("store") ? [TWO_CARDS[1]] : TWO_CARDS),
    );
    await renderListings();
    await screen.findByText("2 offres · par heure de cueillette");

    await userEvent.click(screen.getByRole("button", { name: "Commerce" }));
    let sheet = await screen.findByRole("dialog", { name: "Commerce" });
    await userEvent.click(within(sheet).getByRole("radio", { name: "Épicerie du Quartier" }));

    await waitFor(() =>
      expect(listingRequests(fetchMock)).toContain(
        `/api/listings/?store=${NEIGHBOURHOOD_GROCERY.id}`,
      ),
    );
    expect(await screen.findByText("1 offre · par heure de cueillette")).toBeVisible();

    await userEvent.click(screen.getByRole("button", { name: "Épicerie du Quartier" }));
    sheet = await screen.findByRole("dialog", { name: "Commerce" });
    expect(within(sheet).getByRole("radio", { name: "Boulangerie du Coin" })).toBeVisible();
    expect(within(sheet).getByRole("radio", { name: "Épicerie du Quartier" })).toBeChecked();
  });

  it("explains when nothing matches the filters, and clears them", async () => {
    mockBrowseApi((url) => page(url.searchParams.has("today") ? [] : TWO_CARDS));
    const { container } = await renderListings("/listings?today=1");

    expect(await screen.findByText("Aucune offre pour ces filtres")).toBeVisible();
    await expectNoAxeViolations(container);
    await userEvent.click(screen.getByRole("button", { name: "Effacer les filtres" }));

    expect(await screen.findByText("2 offres · par heure de cueillette")).toBeVisible();
    expect(screen.getByRole("button", { name: "Aujourd'hui" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
  });

  it("says so when there is nothing to see yet", async () => {
    mockBrowseApi(() => page([]));
    await renderListings();

    expect(await screen.findByText("Aucune offre pour le moment")).toBeVisible();
    expect(screen.queryByRole("button", { name: "Effacer les filtres" })).not.toBeInTheDocument();
  });

  it("explains that listings wait for the file's approval", async () => {
    mockBrowseApi(notApproved);
    const { container } = await renderListings();

    expect(
      await screen.findByText("Les offres seront visibles quand votre dossier sera approuvé"),
    ).toBeVisible();
    // The household home, where the file's status will be, is not built yet (FIX-13).
    expect(
      screen.queryByRole("link", { name: "Voir l'état de mon dossier" }),
    ).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Aujourd'hui" })).not.toBeInTheDocument();
    await expectNoAxeViolations(container);
  });

  it("offers to try again after a server failure", async () => {
    let calls = 0;
    mockBrowseApi(() => {
      calls += 1;
      return calls === 1 ? new Response(null, { status: 500 }) : page(TWO_CARDS);
    });
    await renderListings();

    expect(await screen.findByText("Impossible d'afficher cette page")).toBeVisible();
    await userEvent.click(screen.getByRole("button", { name: "Réessayer" }));
    expect(await screen.findByText("2 offres · par heure de cueillette")).toBeVisible();
  });

  it("loads the next 20 listings on request", async () => {
    const fetchMock = mockBrowseApi((url) =>
      url.searchParams.get("page") === "2"
        ? page([TWO_CARDS[1]], { count: 2 })
        : page([TWO_CARDS[0]], { count: 2, next: "http://testserver/api/listings/?page=2" }),
    );
    await renderListings();
    expect(await screen.findByText("2 offres · par heure de cueillette")).toBeVisible();
    expect(cardTitles()).toEqual(["Pains de la veille"]);

    await userEvent.click(screen.getByRole("button", { name: "Afficher plus d'offres" }));

    await waitFor(() => expect(cardTitles()).toEqual(["Pains de la veille", "Savons"]));
    expect(listingRequests(fetchMock)).toContain("/api/listings/?page=2");
    expect(
      screen.queryByRole("button", { name: "Afficher plus d'offres" }),
    ).not.toBeInTheDocument();
  });

  it("opens a listing without asking the server again, and comes back to the same filters", async () => {
    const fetchMock = mockBrowseApi(() => page(TWO_CARDS));
    await renderListings("/listings?today=1");
    await userEvent.click(await screen.findByRole("link", { name: /Pains de la veille/ }));

    expect(await screen.findByRole("heading", { name: "Offre", level: 1 })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Pains de la veille", level: 2 })).toBeVisible();
    expect(listingRequests(fetchMock)).toEqual(["/api/listings/?today=true"]);
    expect(screen.getByRole("link", { name: "Retour" })).toHaveAttribute(
      "href",
      "/listings?today=1",
    );
  });

  it("reads in English", async () => {
    mockBrowseApi(() => page(TWO_CARDS));
    await renderListings();
    await screen.findByText("2 offres · par heure de cueillette");
    await act(async () => {
      await i18n.changeLanguage("en");
    });

    expect(screen.getByText("2 listings · by pickup time")).toBeVisible();
    expect(screen.getByRole("button", { name: "Today" })).toBeVisible();
    expect(screen.getByText("Today · 4 p.m. – 6 p.m.")).toBeVisible();
    expect(screen.getByText("1 bundle left")).toBeVisible();
  });
});
