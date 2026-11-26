// AI contribution: 50% or more AI-generated
import { act, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "../../../app/App";
import i18n from "../../../shared/i18n";
import { expectNoAxeViolations, renderWithProviders } from "../../../test/render";
import { entry, historyPage, historyRequests, mockHistoryApi, pickedUp } from "./testReservations";

async function renderReservations() {
  const view = renderWithProviders(<App />, { route: "/reservations" });
  await screen.findByRole("heading", { name: "Mes réservations", level: 1 });
  return view;
}

/** The card whose title is `name`, such as "Légumes racines × 2". */
const card = (name: string) => screen.getByRole("article", { name });

beforeEach(() => {
  // Thursday 12 November 2026, 09:00 in Montreal.
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date("2026-11-12T14:00:00Z"));
});

afterEach(() => {
  vi.useRealTimers();
});

describe("Pickup history (US-48)", () => {
  it("shows the date, store, item, quantity and status of a pickup", async () => {
    mockHistoryApi(() => historyPage([pickedUp()]));
    const { container } = await renderReservations();

    const vegetables = await screen.findByRole("article", { name: "Légumes racines × 2" });
    expect(within(vegetables).getByText("Récupérée hier à 17 h 20")).toBeVisible();
    expect(within(vegetables).getByText("Épicerie du Quartier")).toBeVisible();
    expect(within(vegetables).getByText("1234, rue Exemple, Montréal H2X 1Y4")).toBeVisible();
    expect(within(vegetables).getByText("Récupérée")).toBeVisible();
    expect(screen.getByRole("heading", { name: "Historique des cueillettes" })).toBeVisible();
    await expectNoAxeViolations(container);
  });

  it("lists upcoming reservations first, with their pickup code and window", async () => {
    mockHistoryApi(() => historyPage([entry(), pickedUp()]));
    const { container } = await renderReservations();

    const headings = await screen.findAllByRole("heading", { level: 2 });
    expect(headings.map((heading) => heading.textContent)).toEqual([
      "1 réservation à venir",
      "Historique des cueillettes",
    ]);
    const bread = card("Pains de la veille × 1");
    expect(within(bread).getByText("Aujourd'hui · 16 h – 18 h")).toBeVisible();
    expect(within(bread).getByText("Code de cueillette : K 7 M 2 Q X")).toBeInTheDocument();
    expect(within(bread).getByText("Réservée")).toBeVisible();
    expect(within(card("Légumes racines × 2")).queryByText(/Code de cueillette/)).toBeNull();
    await expectNoAxeViolations(container);
  });

  it("counts every upcoming reservation, not only the ones loaded so far", async () => {
    mockHistoryApi(() =>
      historyPage([entry()], {
        count: 25,
        upcomingCount: 21,
        next: "/api/reservations/me/?page=2",
      }),
    );
    await renderReservations();

    expect(await screen.findByRole("heading", { name: "21 réservations à venir" })).toBeVisible();
    expect(screen.getAllByRole("article")).toHaveLength(1);
  });

  it("shows the window of a reservation that was not picked up, and why it was cancelled", async () => {
    mockHistoryApi(() =>
      historyPage([
        pickedUp({
          id: "00000000-0000-4000-8000-000000000303",
          status: "cancelled_by_store",
          title: "Yogourts nature",
          picked_up_at: null,
        }),
        pickedUp({
          id: "00000000-0000-4000-8000-000000000304",
          status: "no_show",
          title: "Savons",
          quantity: 1,
          pickup_start: "2026-11-09T15:00:00Z",
          pickup_end: "2026-11-09T17:00:00Z",
          picked_up_at: null,
        }),
      ]),
    );
    await renderReservations();

    const yogurt = await screen.findByRole("article", { name: "Yogourts nature × 2" });
    expect(within(yogurt).getByText("Hier · 16 h – 18 h")).toBeVisible();
    expect(within(yogurt).getByText("Annulée par le commerce")).toBeVisible();
    expect(within(yogurt).getByRole("status")).toHaveTextContent(
      "Le commerce a annulé cette offre. Aucun avertissement n'est ajouté à votre dossier.",
    );
    const soap = card("Savons × 1");
    expect(within(soap).getByText("lun. 9 nov. · 10 h – 12 h")).toBeVisible();
    expect(within(soap).getByText("Absence")).toBeVisible();
    expect(within(soap).queryByRole("status")).toBeNull();
  });

  it("offers the listings when nothing is reserved or picked up yet", async () => {
    mockHistoryApi(() => historyPage([]));
    const { container } = await renderReservations();

    expect(
      await screen.findByRole("heading", { name: "Aucune réservation en cours" }),
    ).toBeVisible();
    expect(screen.getByRole("link", { name: "Voir les offres" })).toHaveAttribute(
      "href",
      "/listings",
    );
    expect(screen.queryByRole("heading", { name: "Historique des cueillettes" })).toBeNull();
    await expectNoAxeViolations(container);
  });

  it("keeps the history under the empty state when nothing is upcoming", async () => {
    mockHistoryApi(() => historyPage([pickedUp()]));
    await renderReservations();

    expect(
      await screen.findByRole("heading", { name: "Aucune réservation en cours" }),
    ).toBeVisible();
    expect(screen.getByRole("article", { name: "Légumes racines × 2" })).toBeVisible();
  });

  it("loads 20 more when asked, ordered as at page 1's time", async () => {
    const fetchMock = mockHistoryApi((url) =>
      url.searchParams.get("page") === "2"
        ? historyPage([pickedUp({ id: "00000000-0000-4000-8000-000000000399", title: "Savons" })], {
            count: 2,
          })
        : historyPage([pickedUp()], {
            count: 2,
            next: "http://testserver/api/reservations/me/?as_of=2026-11-12T14%3A00%3A00Z&page=2",
          }),
    );
    await renderReservations();
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "Afficher plus de réservations" }));

    expect(await screen.findByRole("article", { name: "Savons × 2" })).toBeVisible();
    expect(historyRequests(fetchMock)).toEqual([
      "/api/reservations/me/",
      "/api/reservations/me/?page=2&as_of=2026-11-12T14%3A00%3A00Z",
    ]);
    expect(screen.queryByRole("button", { name: "Afficher plus de réservations" })).toBeNull();
  });

  it("says when the history cannot be loaded, and tries again", async () => {
    let fail = true;
    const fetchMock = mockHistoryApi(() =>
      fail ? new Response(null, { status: 500 }) : historyPage([pickedUp()]),
    );
    await renderReservations();
    const user = userEvent.setup();

    const retry = await screen.findByRole("button", { name: "Réessayer" });
    expect(historyRequests(fetchMock)).toHaveLength(1);
    fail = false;
    await user.click(retry);

    expect(await screen.findByRole("article", { name: "Légumes racines × 2" })).toBeVisible();
  });

  it("keeps the loaded reservations when the next page fails, and asks for that page again", async () => {
    let fail = true;
    const fetchMock = mockHistoryApi((url) => {
      if (url.searchParams.get("page") !== "2") {
        return historyPage([pickedUp()], {
          count: 2,
          next: "http://testserver/api/reservations/me/?as_of=2026-11-12T14%3A00%3A00Z&page=2",
        });
      }
      if (fail) return new Response(null, { status: 500 });
      const soap = pickedUp({ id: "00000000-0000-4000-8000-000000000399", title: "Savons" });
      return historyPage([soap], { count: 2 });
    });
    await renderReservations();
    const user = userEvent.setup();
    const loadMore = "Afficher plus de réservations";

    await user.click(await screen.findByRole("button", { name: loadMore }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Impossible d'afficher plus de réservations.",
    );
    expect(card("Légumes racines × 2")).toBeVisible();
    fail = false;
    await user.click(screen.getByRole("button", { name: loadMore }));

    expect(await screen.findByRole("article", { name: "Savons × 2" })).toBeVisible();
    expect(screen.queryByRole("alert")).toBeNull();
    const nextPage = "/api/reservations/me/?page=2&as_of=2026-11-12T14%3A00%3A00Z";
    expect(historyRequests(fetchMock)).toEqual(["/api/reservations/me/", nextPage, nextPage]);
  });

  it("marks the Réservations tab", async () => {
    mockHistoryApi(() => historyPage([]));
    await renderReservations();

    const nav = screen.getByRole("navigation", { name: "Navigation principale" });
    expect(within(nav).getByRole("link", { name: "Réservations" })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });

  it("reads in English", async () => {
    mockHistoryApi(() => historyPage([entry(), pickedUp()]));
    await renderReservations();
    await screen.findByRole("article", { name: "Légumes racines × 2" });

    await act(() => i18n.changeLanguage("en"));

    expect(screen.getByRole("heading", { name: "My reservations", level: 1 })).toBeVisible();
    expect(screen.getByRole("heading", { name: "1 upcoming reservation" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Pickup history" })).toBeVisible();
    expect(screen.getByText("Picked up yesterday at 5:20 p.m.")).toBeVisible();
    expect(screen.getByText("Today · 4 p.m. – 6 p.m.")).toBeVisible();
  });
});
