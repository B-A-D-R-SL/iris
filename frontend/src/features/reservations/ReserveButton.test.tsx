// AI contribution: 50% or more AI-generated
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { expectNoAxeViolations, renderWithProviders, testUser } from "../../test/render";
import { ReserveButton, type ReserveButtonProps } from "./ReserveButton";

const LISTING_ID = "00000000-0000-4000-8000-0000000000b1";

const reserved = (quantity = 1) =>
  Response.json(
    {
      id: "00000000-0000-4000-8000-0000000000c1",
      listing_id: LISTING_ID,
      quantity,
      pickup_code: "K7MPX3",
      status: "reserved",
      created_at: "2026-11-09T15:00:00Z",
    },
    { status: 201 },
  );

const refused = (status: number, code: string) =>
  Response.json({ code, message: "server text", fields: {} }, { status });

/** Fakes /api/me/ (a household) and POST /api/reservations/. */
function mockApi(post: () => Response = () => reserved()) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = input instanceof Request ? input.url : String(input);
    if (url.endsWith("/api/me/")) return Response.json(testUser("beneficiary"));
    if (url.endsWith("/api/reservations/") && init?.method === "POST") return post();
    return new Response(null, { status: 404 });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function postedBody(fetchMock: ReturnType<typeof mockApi>) {
  const call = fetchMock.mock.calls.find(([, init]) => init?.method === "POST");
  if (!call) throw new Error("Nothing was posted");
  return JSON.parse(call[1]?.body as string) as Record<string, unknown>;
}

function renderButton(props: Partial<ReserveButtonProps> = {}) {
  return renderWithProviders(
    <ReserveButton
      listingId={LISTING_ID}
      title="Pains de la veille"
      maxPerHousehold={1}
      unitsLeft={5}
      {...props}
    />,
  );
}

const reserveButton = () => screen.getByRole("button", { name: "Réserver" });

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("ReserveButton", () => {
  it("reserves one unit in one tap and shows the pickup code", async () => {
    const fetchMock = mockApi();
    const onReserved = vi.fn();
    const { container } = renderButton({ onReserved });

    await userEvent.click(reserveButton());

    expect(await screen.findByText("K7MPX3")).toBeInTheDocument();
    expect(screen.getByText("Code de cueillette")).toBeInTheDocument();
    expect(postedBody(fetchMock)).toEqual({ listing_id: LISTING_ID, quantity: 1 });
    expect(onReserved).toHaveBeenCalledWith(expect.objectContaining({ pickup_code: "K7MPX3" }));
    await expectNoAxeViolations(container);
  });

  it("hides the quantity picker when a household may take only one", () => {
    mockApi();
    renderButton({ maxPerHousehold: 1 });
    expect(screen.queryByRole("textbox", { name: "Quantité" })).not.toBeInTheDocument();
  });

  it("shows the quantity picker, capped by the units left, when more are allowed", async () => {
    const fetchMock = mockApi(() => reserved(2));
    const { container } = renderButton({ maxPerHousehold: 3, unitsLeft: 2 });

    const picker = screen.getByRole("textbox", { name: "Quantité" });
    expect(screen.getByText("Jusqu'à 2 pour votre foyer.")).toBeInTheDocument();
    await expectNoAxeViolations(container);
    await userEvent.clear(picker);
    await userEvent.type(picker, "2");
    await userEvent.click(reserveButton());

    await screen.findByText("K7MPX3");
    expect(postedBody(fetchMock)).toEqual({ listing_id: LISTING_ID, quantity: 2 });
  });

  it("says sold out and disables the button when no units are left", () => {
    const fetchMock = mockApi();
    renderButton({ unitsLeft: 0 });

    expect(screen.getByText("Désolé, cette offre est épuisée.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Épuisé" })).toBeDisabled();
    expect(fetchMock.mock.calls.some(([, init]) => init?.method === "POST")).toBe(false);
  });

  it("says sold out when the last units went while the page was open", async () => {
    mockApi(() => refused(409, "sold_out"));
    renderButton();

    await userEvent.click(reserveButton());

    expect(await screen.findByText("Désolé, cette offre est épuisée.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Épuisé" })).toBeDisabled();
  });

  it.each([
    [
      409,
      "too_many_active_reservations",
      "Vous avez déjà le nombre maximal de réservations en cours.",
    ],
    [400, "quantity_over_listing_limit", "C'est plus qu'un foyer peut réserver pour cette offre."],
    [404, "listing_not_available", "Cette offre n'est plus disponible."],
    [403, "household_not_approved", "Seuls les foyers approuvés peuvent réserver."],
    [503, "reservations_unavailable", "La réservation n'est pas disponible pour le moment."],
    [500, "something_else", "La réservation n'a pas pu être faite. Réessayez."],
  ])("shows its own message for a %i %s refusal", async (status, code, message) => {
    mockApi(() => refused(status, code));
    renderButton();

    await userEvent.click(reserveButton());

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(message);
    expect(alert).not.toHaveTextContent("server text");
    await waitFor(() => expect(reserveButton()).toBeEnabled());
  });
});
