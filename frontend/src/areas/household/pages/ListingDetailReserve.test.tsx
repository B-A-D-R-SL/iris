// AI contribution: 50% or more AI-generated
/** Reserving from the listing page (US-41, mockup H1 steps 4 and 5, 4a and 4b). */
import { QueryClient } from "@tanstack/react-query";
import { act, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "../../../app/App";
import { expectNoAxeViolations, renderWithProviders } from "../../../test/render";
import { card, listingRequests, mockBrowseApi, page } from "./testListings";

const ID = "00000000-0000-4000-8000-000000000101";

const reserved = (quantity = 1) =>
  Response.json(
    {
      id: "00000000-0000-4000-8000-0000000000c1",
      listing_id: ID,
      quantity,
      pickup_code: "K7M2QX",
      status: "reserved",
      created_at: "2026-11-12T14:00:00Z",
    },
    { status: 201 },
  );

const refused = (status: number, code: string) => () =>
  Response.json({ code, message: "server text", fields: {} }, { status });

/** The JSON body sent to POST /api/reservations/, or null when nothing was sent. */
function reserveBody(fetchMock: ReturnType<typeof mockBrowseApi>) {
  const call = fetchMock.mock.calls.find(([, init]) => init?.method === "POST");
  return call ? (JSON.parse(call[1]?.body as string) as Record<string, unknown>) : null;
}

async function openListing(reserve: () => Response, overrides = {}) {
  const fetchMock = mockBrowseApi(() => page([card(overrides)]), reserve);
  const view = renderWithProviders(<App />, { route: `/listings/${ID}` });
  await screen.findByRole("heading", { name: "Pains de la veille", level: 2 });
  return { fetchMock, ...view };
}

const reserveButton = () => screen.getByRole("button", { name: "Réserver" });

beforeEach(() => {
  // Thursday 12 November 2026, 09:00 in Montreal.
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date("2026-11-12T14:00:00Z"));
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("Reserving from the listing page (US-41)", () => {
  it("reserves in one tap and shows the code like H1 step 5", async () => {
    const { fetchMock, container } = await openListing(() => reserved(), {
      max_per_household: 1,
    });
    expect(screen.queryByRole("textbox", { name: "Quantité" })).not.toBeInTheDocument();

    await userEvent.click(reserveButton());

    expect(await screen.findByRole("heading", { name: "C'est réservé!" })).toBeVisible();
    expect(screen.getByText("Réservation")).toBeVisible(); // the app bar title
    expect(screen.getByText("K7M2QX")).toHaveAccessibleName("Code de cueillette : K 7 M 2 Q X");
    expect(screen.getByText("Pains de la veille × 1")).toBeVisible();
    const summary = within(screen.getByRole("list"));
    expect(summary.getByText("Boulangerie du Coin")).toBeVisible();
    expect(summary.getByText("Aujourd'hui · 16 h – 18 h")).toBeVisible();
    expect(summary.queryByText(/restants/)).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Voir mes réservations" })).toHaveAttribute(
      "href",
      "/reservations",
    );
    expect(reserveBody(fetchMock)).toEqual({ listing_id: ID, quantity: 1 });
    await expectNoAxeViolations(container);
  });

  it.each([
    ["no longer lists the listing (its last unit was taken)", () => page([])],
    ["fails", () => new Response(null, { status: 500 })],
  ])("keeps the code on screen when the listing, reloaded later, %s", async (_case, after) => {
    let reservedYet = false;
    const fetchMock = mockBrowseApi(
      () => (reservedYet ? after() : page([card({ units_left: 1, max_per_household: 1 })])),
      () => {
        reservedYet = true;
        return reserved();
      },
    );
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    renderWithProviders(<App />, { route: `/listings/${ID}`, queryClient });
    await userEvent.click(await screen.findByRole("button", { name: "Réserver" }));
    expect(await screen.findByRole("heading", { name: "C'est réservé!" })).toBeVisible();
    const before = listingRequests(fetchMock).length;

    // The listing is reloaded later (after a minute, back in the app, on reconnect).
    await act(async () => {
      await queryClient.refetchQueries({ queryKey: ["listing", ID] });
      // React Query hands the result to the page on a timer; let it render.
      await new Promise((resolve) => setTimeout(resolve, 50));
    });

    expect(listingRequests(fetchMock).length).toBeGreaterThan(before);
    expect(screen.getByRole("heading", { name: "C'est réservé!" })).toBeVisible();
    expect(screen.getByText("K7M2QX")).toBeVisible();
    expect(screen.getByText("Pains de la veille × 1")).toBeVisible();
    expect(screen.queryByText("Cette offre n'est plus disponible")).not.toBeInTheDocument();
  });

  it("sends the quantity chosen, up to the household maximum", async () => {
    const { fetchMock } = await openListing(() => reserved(2));
    expect(screen.getByText("2 au maximum pour votre foyer")).toBeVisible();

    const picker = screen.getByRole("textbox", { name: "Quantité" });
    await userEvent.clear(picker);
    await userEvent.type(picker, "2");
    await userEvent.click(reserveButton());

    expect(await screen.findByText("Pains de la veille × 2")).toBeVisible();
    expect(reserveBody(fetchMock)).toEqual({ listing_id: ID, quantity: 2 });
  });

  it("says at the top when the last units went just before (H1 4a)", async () => {
    const { container } = await openListing(refused(409, "sold_out"));

    await userEvent.click(reserveButton());

    const notice = await screen.findByRole("status");
    expect(notice).toHaveTextContent("Cette offre vient d'être réservée au complet");
    expect(notice).not.toHaveTextContent("server text");
    // The notice comes before the listing, as in the mockup.
    const heading = screen.getByRole("heading", { name: "Pains de la veille", level: 2 });
    expect(notice.compareDocumentPosition(heading) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(screen.getByRole("button", { name: "Épuisée" })).toBeDisabled();
    expect(screen.queryByRole("textbox", { name: "Quantité" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Voir d'autres offres" })).toHaveAttribute(
      "href",
      "/listings",
    );
    await expectNoAxeViolations(container);
  });

  it("says at the top when the household is at its limit (H1 4b)", async () => {
    await openListing(refused(409, "too_many_active_reservations"));

    await userEvent.click(reserveButton());

    expect(await screen.findByRole("status")).toHaveTextContent(
      "Vous avez déjà le nombre maximal de réservations actives",
    );
    expect(reserveButton()).toBeDisabled();
    expect(screen.queryByRole("textbox", { name: "Quantité" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Voir mes réservations" })).toHaveAttribute(
      "href",
      "/reservations",
    );
  });

  it("removes the notice when the household changes the quantity after a refusal", async () => {
    let calls = 0;
    await openListing(() => {
      calls += 1;
      return calls === 1 ? refused(409, "not_enough_units")() : reserved();
    });
    await userEvent.click(screen.getByRole("button", { name: "Augmenter (Quantité)" }));
    await userEvent.click(reserveButton());
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Il n'en reste pas assez. Choisissez une plus petite quantité.",
    );

    await userEvent.click(screen.getByRole("button", { name: "Diminuer (Quantité)" }));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();

    await userEvent.click(reserveButton());
    expect(await screen.findByRole("heading", { name: "C'est réservé!" })).toBeVisible();
  });

  it("shows other refusals as an error at the top and lets the household try again", async () => {
    let calls = 0;
    await openListing(() => {
      calls += 1;
      return calls === 1 ? refused(503, "reservations_unavailable")() : reserved();
    });

    await userEvent.click(reserveButton());
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "La réservation n'est pas disponible pour le moment. Réessayez plus tard.",
    );

    await userEvent.click(reserveButton());
    expect(await screen.findByRole("heading", { name: "C'est réservé!" })).toBeVisible();
  });
});
