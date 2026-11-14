// AI contribution: 50% or more AI-generated
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "../../../app/App";
import type { Pickup } from "../../../features/reservations/pickupApi";
import i18n from "../../../shared/i18n";
import { expectNoAxeViolations, renderWithProviders, testUser } from "../../../test/render";

const PICKUP: Pickup = {
  id: "00000000-0000-4000-8000-000000000201",
  status: "reserved",
  holder: "Fatou D.",
  alternate: "Paul T.",
  title: "Pains de la veille",
  unit: "item",
  quantity: 1,
  pickup_code: "P4WZ8H",
  pickup_start: "2026-11-12T20:00:00Z",
  pickup_end: "2026-11-12T23:00:00Z",
  picked_up_at: null,
};

let mockScan: ((text: string) => void) | null = null;
let mockCameraStatus: "starting" | "live" | "denied" | "unavailable" = "denied";

vi.mock("../components/PickupScanner", async () => {
  const React = await import("react");
  return {
    PickupScanner: ({
      onDetected,
      onStatus,
    }: {
      active: boolean;
      onDetected: (text: string) => void;
      onStatus: (status: "starting" | "live" | "denied" | "unavailable") => void;
    }) => {
      React.useEffect(() => {
        mockScan = onDetected;
        onStatus(mockCameraStatus);
      }, [onDetected, onStatus]);
      return <div data-testid="pickup-scanner" />;
    },
  };
});

function refusal(code: string, picked_up_at: string | null = null) {
  return Response.json(
    { code, message: code, fields: {}, ...(picked_up_at ? { picked_up_at } : {}) },
    { status: code === "unknown_code" ? 404 : 409 },
  );
}

function mockApi({
  lookup = () => Response.json(PICKUP),
  confirm = () =>
    Response.json({
      ...PICKUP,
      status: "picked_up",
      picked_up_at: "2026-11-12T21:15:00Z",
    }),
}: {
  lookup?: () => Response;
  confirm?: () => Response;
} = {}) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = input instanceof Request ? input.url : String(input);
    if (url.endsWith("/api/me/")) return Response.json(testUser("store_staff"));
    if (url.endsWith("/api/store/pickups/lookup/") && init?.method === "POST") return lookup();
    if (
      url.includes("/api/store/pickups/") &&
      url.endsWith("/confirm/") &&
      init?.method === "POST"
    ) {
      return confirm();
    }
    return new Response(null, { status: 404 });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

async function renderConfirm() {
  const view = renderWithProviders(<App />, { route: "/store/confirm" });
  await screen.findByRole("heading", { name: "Confirmer la cueillette", level: 1 });
  return view;
}

async function typeCode(code: string) {
  await userEvent.clear(screen.getByLabelText("Code de cueillette"));
  await userEvent.type(screen.getByLabelText("Code de cueillette"), code);
}

beforeEach(async () => {
  mockScan = null;
  mockCameraStatus = "denied";
  await i18n.changeLanguage("fr");
  document.cookie = "csrftoken=test-csrf; path=/";
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date("2026-11-12T21:00:00Z"));
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("Confirm pickup scan screen (US-44 / T-06.44.3)", () => {
  it("looks up a typed code, shows who and what, then confirms in one tap", async () => {
    const fetchMock = mockApi();
    const { container } = await renderConfirm();

    expect(screen.getByTestId("pickup-scanner")).toBeInTheDocument();
    expect(screen.getByText(/Tapez le code de 6 caractères/)).toBeVisible();

    await typeCode("p4wz8h");
    await userEvent.click(screen.getByRole("button", { name: "Vérifier la réservation" }));

    expect(
      await screen.findByRole("heading", { name: "Vérifier la réservation", level: 2 }),
    ).toBeVisible();
    expect(screen.getByText("Fatou D.")).toBeVisible();
    expect(screen.getByText("Paul T.")).toBeVisible();
    expect(screen.getByText("Pains de la veille")).toBeVisible();
    expect(screen.getByText(/1 · Article/)).toBeVisible();
    expect(screen.getByText("P4WZ8H")).toBeVisible();

    const lookupCall = fetchMock.mock.calls.find((call) =>
      String(call[0]).endsWith("/api/store/pickups/lookup/"),
    );
    expect(JSON.parse(String(lookupCall?.[1]?.body))).toEqual({ code: "P4WZ8H" });

    await userEvent.click(screen.getByRole("button", { name: "Confirmer la remise" }));
    expect(await screen.findByText("Cueillette confirmée")).toBeVisible();
    expect(screen.getByText(/Remise effectuée pour Fatou D/)).toBeVisible();
    expect(screen.getByRole("link", { name: "Retour à Aujourd'hui" })).toHaveAttribute(
      "href",
      "/store/listings/new",
    );

    await expectNoAxeViolations(container);
  });

  it("looks up a decoded scan and shows the matching pickup", async () => {
    mockCameraStatus = "live";
    const fetchMock = mockApi();
    await renderConfirm();
    await waitFor(() => expect(mockScan).not.toBeNull());

    mockScan?.("p4wz8h");

    expect(
      await screen.findByRole("heading", { name: "Vérifier la réservation", level: 2 }),
    ).toBeVisible();
    expect(screen.getByText("Fatou D.")).toBeVisible();
    const lookupCall = fetchMock.mock.calls.find((call) =>
      String(call[0]).endsWith("/api/store/pickups/lookup/"),
    );
    expect(JSON.parse(String(lookupCall?.[1]?.body))).toEqual({ code: "P4WZ8H" });
  });

  it("shows a clear message for an unknown code and keeps the typed fallback", async () => {
    mockApi({ lookup: () => refusal("unknown_code") });
    await renderConfirm();

    await typeCode("ZZZZZZ");
    await userEvent.click(screen.getByRole("button", { name: "Vérifier la réservation" }));

    expect(await screen.findByText("Code introuvable")).toBeVisible();
    expect(screen.getByText(/Aucune réservation de votre commerce n'a ce code/)).toBeVisible();
    expect(screen.getByLabelText("Code de cueillette")).toBeVisible();
  });

  it("refuses a wrong-store, already-picked-up and cancelled code", async () => {
    const fetchMock = mockApi({
      lookup: () => refusal("wrong_store"),
    });
    await renderConfirm();
    await typeCode("P4WZ8H");
    await userEvent.click(screen.getByRole("button", { name: "Vérifier la réservation" }));
    expect(await screen.findByText("À récupérer ailleurs")).toBeVisible();

    fetchMock.mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = input instanceof Request ? input.url : String(input);
      if (url.endsWith("/api/me/")) return Response.json(testUser("store_staff"));
      if (url.endsWith("/api/store/pickups/lookup/") && init?.method === "POST") {
        return refusal("already_picked_up", "2026-11-12T20:30:00Z");
      }
      return new Response(null, { status: 404 });
    });
    await userEvent.click(screen.getByRole("button", { name: "Vérifier la réservation" }));
    expect(await screen.findByText("Déjà récupérée")).toBeVisible();
    expect(screen.getByText(/Première confirmation à/)).toBeVisible();

    fetchMock.mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = input instanceof Request ? input.url : String(input);
      if (url.endsWith("/api/me/")) return Response.json(testUser("store_staff"));
      if (url.endsWith("/api/store/pickups/lookup/") && init?.method === "POST") {
        return refusal("cancelled");
      }
      return new Response(null, { status: 404 });
    });
    await userEvent.click(screen.getByRole("button", { name: "Vérifier la réservation" }));
    expect(await screen.findByText("Réservation annulée")).toBeVisible();
  });

  it("returns to the scanner after cancel, and after scanning another code", async () => {
    mockApi();
    await renderConfirm();
    await typeCode("P4WZ8H");
    await userEvent.click(screen.getByRole("button", { name: "Vérifier la réservation" }));
    expect(await screen.findByText("Fatou D.")).toBeVisible();

    await userEvent.click(screen.getByRole("button", { name: "Annuler" }));
    expect(await screen.findByLabelText("Code de cueillette")).toHaveValue("");

    await typeCode("P4WZ8H");
    await userEvent.click(screen.getByRole("button", { name: "Vérifier la réservation" }));
    await userEvent.click(await screen.findByRole("button", { name: "Confirmer la remise" }));
    expect(await screen.findByText("Cueillette confirmée")).toBeVisible();

    await userEvent.click(screen.getByRole("button", { name: "Scanner un autre code" }));
    await waitFor(() => expect(screen.getByLabelText("Code de cueillette")).toHaveValue(""));
  });

  it("shows the camera-unavailable hint while keeping typed entry", async () => {
    mockCameraStatus = "unavailable";
    mockApi();
    await renderConfirm();
    expect(await screen.findByText("Caméra indisponible")).toBeVisible();
    expect(screen.getByText(/Cet appareil n'a pas de caméra/)).toBeVisible();
    expect(screen.getByLabelText("Code de cueillette")).toBeVisible();
  });

  it("keeps review on a transient confirm failure, then returns on a hard refusal", async () => {
    const fetchMock = mockApi({
      confirm: () => new Response("down", { status: 502 }),
    });
    await renderConfirm();
    await typeCode("P4WZ8H");
    await userEvent.click(screen.getByRole("button", { name: "Vérifier la réservation" }));
    expect(await screen.findByText("Fatou D.")).toBeVisible();

    await userEvent.click(screen.getByRole("button", { name: "Confirmer la remise" }));
    expect(await screen.findByText("Serveur injoignable")).toBeVisible();
    expect(screen.getByText("Fatou D.")).toBeVisible();
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Confirmer la remise" })).toBeEnabled(),
    );

    fetchMock.mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = input instanceof Request ? input.url : String(input);
      if (url.endsWith("/api/me/")) return Response.json(testUser("store_staff"));
      if (url.endsWith("/api/store/pickups/lookup/") && init?.method === "POST") {
        return Response.json(PICKUP);
      }
      if (url.includes("/confirm/") && init?.method === "POST") {
        return refusal("cancelled");
      }
      return new Response(null, { status: 404 });
    });
    await userEvent.click(screen.getByRole("button", { name: "Confirmer la remise" }));
    expect(await screen.findByText("Réservation annulée")).toBeVisible();
    expect(screen.getByLabelText("Code de cueillette")).toBeVisible();
  });

  it("normalizes a pasted code before enforcing its length", async () => {
    const user = userEvent.setup();
    mockApi();
    await renderConfirm();

    const input = screen.getByLabelText("Code de cueillette");
    await user.click(input);
    await user.paste("p4 wz8h");

    expect(input).toHaveValue("P4WZ8H");
    expect(screen.getByRole("button", { name: "Vérifier la réservation" })).toBeEnabled();

    await user.click(screen.getByRole("button", { name: "Vérifier la réservation" }));
    expect(await screen.findByText("Fatou D.")).toBeVisible();
  });

  it("shows a network failure on review and allows confirmation retry", async () => {
    let offline = true;
    mockApi({
      confirm: () => {
        if (offline) throw new TypeError("Failed to fetch");
        return Response.json({
          ...PICKUP,
          status: "picked_up",
          picked_up_at: "2026-11-12T21:15:00Z",
        });
      },
    });
    await renderConfirm();
    await typeCode("P4WZ8H");
    await userEvent.click(screen.getByRole("button", { name: "Vérifier la réservation" }));
    await screen.findByText("Fatou D.");

    await userEvent.click(screen.getByRole("button", { name: "Confirmer la remise" }));
    expect(await screen.findByText("Serveur injoignable")).toBeVisible();
    expect(screen.getByText("Fatou D.")).toBeVisible();
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Confirmer la remise" })).toBeEnabled(),
    );

    offline = false;
    await userEvent.click(screen.getByRole("button", { name: "Confirmer la remise" }));
    expect(await screen.findByText("Cueillette confirmée")).toBeVisible();
  });

  it("does not carry a confirmation refusal into another pickup review", async () => {
    let currentPickup = PICKUP;
    mockApi({
      lookup: () => Response.json(currentPickup),
      confirm: () => refusal("cancelled"),
    });
    await renderConfirm();
    await typeCode("P4WZ8H");
    await userEvent.click(screen.getByRole("button", { name: "Vérifier la réservation" }));
    await screen.findByText("Fatou D.");
    await userEvent.click(screen.getByRole("button", { name: "Confirmer la remise" }));
    expect(await screen.findByText("Réservation annulée")).toBeVisible();

    currentPickup = {
      ...PICKUP,
      id: "00000000-0000-4000-8000-000000000202",
      pickup_code: "B7K9M2",
      holder: "Test holder B",
    };
    await typeCode("B7K9M2");
    await userEvent.click(screen.getByRole("button", { name: "Vérifier la réservation" }));

    expect(await screen.findByText("Test holder B")).toBeVisible();
    expect(screen.queryByText("Réservation annulée")).not.toBeInTheDocument();
  });
});
