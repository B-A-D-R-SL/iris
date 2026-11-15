// AI contribution: 50% or more AI-generated
/** The admin store list (US-14, Figma W7.1, W7.2b, W7.4). */
import { act, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import App from "../../../app/App";
import i18n from "../../../shared/i18n";
import { expectNoAxeViolations, renderWithProviders } from "../../../test/render";
import { demoStore, mockStoreApi, storePage } from "../../../test/staffStores";
import { Stores } from "./Stores";

const cafe = {
  ...demoStore,
  id: "00000000-0000-4000-8000-0000000000bb",
  name: "Café Démo",
  street_number: "88",
  street_name: "rue Ontario E",
  is_active: false,
  open_listings: 0,
};

describe("Stores", () => {
  it("lists stores with address, open listings, status and an edit link, in French", async () => {
    mockStoreApi({ list: () => Response.json(storePage([demoStore, cafe])) });
    const { container } = renderWithProviders(<Stores />);

    expect(await screen.findByText("Épicerie Démo du Quartier")).toBeInTheDocument();
    expect(screen.getByText("1234 rue Saint-Denis")).toBeInTheDocument();
    expect(screen.getByText("Actif")).toBeInTheDocument();
    expect(screen.getByText("Désactivé")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Commerces" })).toBeInTheDocument();
    expect(screen.getByText("Tous · 2")).toBeInTheDocument();
    expect(screen.getByText("Actifs · 1")).toBeInTheDocument();
    expect(screen.getByText("Désactivés · 1")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Modifier Café Démo" })).toHaveAttribute(
      "href",
      `/staff/stores/${cafe.id}`,
    );
    await expectNoAxeViolations(container);
  });

  it("searches and filters on the server, back to page 1", async () => {
    const fetchMock = mockStoreApi();
    renderWithProviders(<Stores />);
    await screen.findByText("Épicerie Démo du Quartier");

    await userEvent.type(screen.getByLabelText("Chercher un commerce"), "ontario");
    await userEvent.click(screen.getByText("Désactivés · 0"));

    await waitFor(() => {
      const urls = fetchMock.mock.calls.map(([input]) => String(input));
      expect(urls.some((url) => url.includes("q=ontario") && url.includes("status=inactive"))).toBe(
        true,
      );
    });
  });

  it("explains when nothing matches", async () => {
    mockStoreApi({ list: () => Response.json(storePage([])) });
    renderWithProviders(<Stores />);
    expect(await screen.findByText("Aucun commerce trouvé")).toBeInTheDocument();
  });

  it("offers a retry when the list fails", async () => {
    mockStoreApi({ list: () => new Response(null, { status: 500 }) });
    renderWithProviders(<Stores />);
    expect(await screen.findByRole("button", { name: /réessayer/i })).toBeInTheDocument();
  });

  it("is in English when the language is switched", async () => {
    mockStoreApi();
    renderWithProviders(<Stores />);
    await screen.findByText("Épicerie Démo du Quartier");
    await act(() => i18n.changeLanguage("en"));
    expect(await screen.findByRole("heading", { name: "Stores" })).toBeInTheDocument();
    expect(screen.getByText("All · 1")).toBeInTheDocument();
    await act(() => i18n.changeLanguage("fr"));
  });

  it("is reached from the admin side nav only", async () => {
    mockStoreApi();
    renderWithProviders(<App />, { route: "/staff/stores" });
    expect(await screen.findByText("Épicerie Démo du Quartier")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Commerces" })).toBeInTheDocument();
  });

  it("is refused to intake workers", async () => {
    mockStoreApi({ role: "intake_worker" });
    renderWithProviders(<App />, { route: "/staff/stores" });
    await waitFor(() => expect(screen.queryByText("Épicerie Démo du Quartier")).toBeNull());
    expect(screen.queryByRole("link", { name: "Commerces" })).toBeNull();
  });
});
