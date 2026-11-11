// AI contribution: 50% or more AI-generated
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "../../../app/App";
import { expectNoAxeViolations, renderWithProviders } from "../../../test/render";
import {
  card,
  CORNER_BAKERY,
  listingRequests,
  mockBrowseApi,
  notApproved,
  page,
} from "./testListings";

const ID = "00000000-0000-4000-8000-000000000101";
const OTHER = card({ id: "00000000-0000-4000-8000-000000000199", title: "Autre offre" });

beforeEach(() => {
  // Thursday 12 November 2026, 09:00 in Montreal.
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date("2026-11-12T14:00:00Z"));
});

afterEach(() => {
  vi.useRealTimers();
});

describe("Listing detail (US-36)", () => {
  it("finds a listing opened from a link and shows it like H1.4, without reserving", async () => {
    const fetchMock = mockBrowseApi((url) =>
      url.searchParams.get("page") === "2"
        ? page([card({ store: { ...CORNER_BAKERY, unit: "5" } })])
        : page([OTHER], { next: "http://testserver/api/listings/?page=2" }),
    );
    const { container } = renderWithProviders(<App />, { route: `/listings/${ID}` });

    expect(
      await screen.findByRole("heading", { name: "Pains de la veille", level: 2 }),
    ).toBeVisible();
    expect(listingRequests(fetchMock)).toEqual(["/api/listings/", "/api/listings/?page=2"]);
    expect(await screen.findByText("Boulangerie")).toBeVisible();

    const facts = within(screen.getByRole("list"));
    expect(facts.getByText("Boulangerie du Coin")).toBeVisible();
    expect(facts.getByText("1234, rue Exemple, local 5, Montréal H2X 1Y4")).toBeVisible();
    expect(facts.getByText("Aujourd'hui · 16 h – 18 h")).toBeVisible();
    expect(facts.getByText("Meilleur avant le 13 nov. 2026")).toBeVisible();
    expect(facts.getByText("7 restants")).toBeVisible();

    // Reserving arrives with US-41.
    expect(screen.queryByRole("button", { name: /Réserver/ })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Retour" })).toHaveAttribute("href", "/listings");
    await expectNoAxeViolations(container);
  });

  it("says when the listing is no longer available", async () => {
    mockBrowseApi(() => page([OTHER]));
    renderWithProviders(<App />, { route: `/listings/${ID}` });

    expect(await screen.findByText("Cette offre n'est plus disponible")).toBeVisible();
    expect(screen.getByRole("link", { name: "Voir les offres" })).toHaveAttribute(
      "href",
      "/listings",
    );
  });

  it("offers to try again after a server failure", async () => {
    let calls = 0;
    mockBrowseApi(() => {
      calls += 1;
      return calls === 1 ? new Response(null, { status: 503 }) : page([card()]);
    });
    renderWithProviders(<App />, { route: `/listings/${ID}` });

    expect(await screen.findByText("Impossible d'afficher cette page")).toBeVisible();
    await userEvent.click(screen.getByRole("button", { name: "Réessayer" }));
    expect(
      await screen.findByRole("heading", { name: "Pains de la veille", level: 2 }),
    ).toBeVisible();
  });

  it("explains that listings wait for the file's approval", async () => {
    mockBrowseApi(notApproved);
    renderWithProviders(<App />, { route: `/listings/${ID}` });

    expect(
      await screen.findByText("Les offres seront visibles quand votre dossier sera approuvé"),
    ).toBeVisible();
  });
});
