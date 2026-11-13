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
  const callbacks = { onReserved: vi.fn(), onRefused: vi.fn() };
  const view = renderWithProviders(
    <ReserveButton
      listingId={LISTING_ID}
      maxPerHousehold={1}
      unitsLeft={5}
      {...callbacks}
      {...props}
    />,
  );
  return { ...view, ...callbacks };
}

const reserveButton = () => screen.getByRole("button", { name: "Réserver" });

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("ReserveButton", () => {
  it("reserves one unit in one tap and hands the reservation to the page", async () => {
    const fetchMock = mockApi();
    const { container, onReserved, onRefused } = renderButton();

    await userEvent.click(reserveButton());

    await waitFor(() =>
      expect(onReserved).toHaveBeenCalledWith(expect.objectContaining({ pickup_code: "K7MPX3" })),
    );
    // Only the clearing call made when the request starts: no refusal.
    expect(onRefused.mock.calls).toEqual([[null]]);
    expect(postedBody(fetchMock)).toEqual({ listing_id: LISTING_ID, quantity: 1 });
    await expectNoAxeViolations(container);
  });

  it("hides the quantity picker when a household may take only one", () => {
    mockApi();
    renderButton({ maxPerHousehold: 1 });
    expect(screen.queryByRole("textbox", { name: "Quantité" })).not.toBeInTheDocument();
  });

  it("steps the quantity with − and +, capped by the units left", async () => {
    const fetchMock = mockApi(() => reserved(2));
    const { container, onReserved } = renderButton({ maxPerHousehold: 3, unitsLeft: 2 });

    const picker = screen.getByRole("textbox", { name: "Quantité" });
    const minus = screen.getByRole("button", { name: "Diminuer (Quantité)" });
    const plus = screen.getByRole("button", { name: "Augmenter (Quantité)" });
    // The help text names the household maximum; the cap also follows units left.
    expect(screen.getByText("3 au maximum pour votre foyer")).toBeInTheDocument();
    expect(minus).toBeDisabled();
    await expectNoAxeViolations(container);

    await userEvent.click(plus);
    expect(picker).toHaveValue("2");
    expect(plus).toBeDisabled();
    await userEvent.click(reserveButton());

    await waitFor(() => expect(onReserved).toHaveBeenCalled());
    expect(postedBody(fetchMock)).toEqual({ listing_id: LISTING_ID, quantity: 2 });
  });

  it("never sends more than the cap, even when more is typed", async () => {
    const fetchMock = mockApi(() => reserved(2));
    const { onReserved } = renderButton({ maxPerHousehold: 3, unitsLeft: 2 });

    const picker = screen.getByRole("textbox", { name: "Quantité" });
    await userEvent.clear(picker);
    await userEvent.type(picker, "9");
    await userEvent.click(reserveButton());

    await waitFor(() => expect(onReserved).toHaveBeenCalled());
    expect(postedBody(fetchMock)).toEqual({ listing_id: LISTING_ID, quantity: 2 });
  });

  it("shows Épuisée, disabled, and a way to other listings when none are left", () => {
    const fetchMock = mockApi();
    renderButton({ unitsLeft: 0 });

    expect(screen.getByRole("button", { name: "Épuisée" })).toBeDisabled();
    expect(screen.getByRole("link", { name: "Voir d'autres offres" })).toHaveAttribute(
      "href",
      "/listings",
    );
    expect(fetchMock.mock.calls.some(([, init]) => init?.method === "POST")).toBe(false);
  });

  it("reports a sold-out refusal and switches to Épuisée", async () => {
    mockApi(() => refused(409, "sold_out"));
    const { onRefused } = renderButton();

    await userEvent.click(reserveButton());

    await waitFor(() => expect(onRefused).toHaveBeenCalledWith("sold_out"));
    expect(screen.getByRole("button", { name: "Épuisée" })).toBeDisabled();
    expect(screen.getByRole("link", { name: "Voir d'autres offres" })).toBeInTheDocument();
  });

  it("reports the limit and offers the household's reservations instead", async () => {
    mockApi(() => refused(409, "too_many_active_reservations"));
    const { onRefused } = renderButton();

    await userEvent.click(reserveButton());

    await waitFor(() => expect(onRefused).toHaveBeenCalledWith("too_many_active_reservations"));
    expect(reserveButton()).toBeDisabled();
    expect(screen.getByRole("link", { name: "Voir mes réservations" })).toHaveAttribute(
      "href",
      "/reservations",
    );
  });

  it.each([
    [400, "quantity_over_listing_limit"],
    [404, "listing_not_available"],
    [503, "reservations_unavailable"],
  ])("reports a %i %s refusal and lets the household try again", async (status, code) => {
    mockApi(() => refused(status, code));
    const { onRefused } = renderButton();

    await userEvent.click(reserveButton());

    await waitFor(() => expect(onRefused).toHaveBeenCalledWith(code));
    expect(reserveButton()).toBeEnabled();
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });

  it("clears a refusal when the quantity changes, then when the household retries", async () => {
    let calls = 0;
    mockApi(() => {
      calls += 1;
      return calls === 1 ? refused(409, "not_enough_units") : reserved();
    });
    const { onRefused, onReserved } = renderButton({ maxPerHousehold: 3, unitsLeft: 3 });
    await userEvent.click(screen.getByRole("button", { name: "Augmenter (Quantité)" }));
    await userEvent.click(reserveButton());
    await waitFor(() => expect(onRefused).toHaveBeenLastCalledWith("not_enough_units"));

    onRefused.mockClear();
    await userEvent.click(screen.getByRole("button", { name: "Diminuer (Quantité)" }));
    expect(onRefused).toHaveBeenCalledWith(null);

    onRefused.mockClear();
    await userEvent.click(reserveButton());
    await waitFor(() => expect(onReserved).toHaveBeenCalled());
    expect(onRefused.mock.calls).toEqual([[null]]);
  });

  it("reports a lost connection as a generic refusal", async () => {
    mockApi(() => {
      throw new TypeError("Failed to fetch");
    });
    const { onRefused } = renderButton();

    await userEvent.click(reserveButton());

    await waitFor(() => expect(onRefused).toHaveBeenCalledWith("request_refused"));
    expect(reserveButton()).toBeEnabled();
  });
});
