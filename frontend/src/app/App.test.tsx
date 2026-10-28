// AI contribution: 50% or more AI-generated
import { act, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import type { Role } from "../features/accounts/currentUser";
import i18n from "../shared/i18n";
import {
  expectNoAxeViolations,
  mockCurrentUser,
  renderWithProviders,
  testUser,
} from "../test/render";
import App from "./App";

function renderApp(route: string, user: Role | "signed-out" | "server-error") {
  mockCurrentUser(user === "signed-out" || user === "server-error" ? user : testUser(user));
  return renderWithProviders(<App />, { route });
}

const mainNav = () => screen.getByRole("navigation", { name: "Navigation principale" });
const staffNav = () => screen.getByRole("navigation", { name: "Votre espace" });
const linkNames = (nav: HTMLElement) =>
  within(nav)
    .getAllByRole("link")
    .map((link) => link.textContent);

describe("public area", () => {
  it("welcomes visitors with sign in, register and become a partner", async () => {
    const { container } = renderApp("/", "signed-out");

    expect(await screen.findByRole("heading", { name: "Bienvenue sur Iris" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Connexion" })).toHaveAttribute("href", "/sign-in");
    expect(screen.getByRole("link", { name: "Inscrire mon foyer" })).toHaveAttribute(
      "href",
      "/sign-up",
    );
    expect(screen.getByRole("link", { name: "Devenir partenaire" })).toHaveAttribute(
      "href",
      "/partner/apply",
    );
    await expectNoAxeViolations(container);
  });

  it("switches the whole page to English", async () => {
    renderApp("/", "signed-out");
    await userEvent.click(await screen.findByRole("button", { name: "English" }));
    expect(screen.getByRole("heading", { name: "Welcome to Iris" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Become a partner" })).toBeInTheDocument();
  });

  it("sends a signed-in user from the welcome page to their own home", async () => {
    renderApp("/", "store_staff");
    expect(await screen.findByRole("heading", { name: "Aujourd'hui" })).toBeInTheDocument();
  });

  it("explains an unknown address", async () => {
    renderApp("/nowhere", "signed-out");
    expect(await screen.findByRole("heading", { name: "Page introuvable" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Retour à l'accueil" })).toHaveAttribute("href", "/");
  });
});

describe("guards (deny by default)", () => {
  it.each(["/home", "/store/listings/new", "/staff/households"])(
    "sends a signed-out visitor from %s to sign-in",
    async (route) => {
      renderApp(route, "signed-out");
      expect(await screen.findByRole("heading", { name: "Connexion" })).toBeInTheDocument();
    },
  );

  it.each([
    ["beneficiary", "/store/listings/new", "Accueil"],
    ["beneficiary", "/staff/partners", "Accueil"],
    ["store_staff", "/listings", "Aujourd'hui"],
    ["store_manager", "/staff/households", "Aujourd'hui"],
    ["intake_worker", "/store", "Foyers"],
    ["admin", "/reservations", "Foyers"],
  ] as const)("sends %s away from %s to their home (%s)", async (role, route, home) => {
    renderApp(route, role);
    expect(await screen.findByRole("heading", { name: home })).toBeInTheDocument();
  });

  it.each([
    "/staff/review",
    "/staff/partners",
    "/staff/stores",
    "/staff/categories",
    "/staff/audit",
  ])("keeps admin-only %s from intake workers", async (route) => {
    renderApp(route, "intake_worker");
    expect(await screen.findByRole("heading", { name: "Foyers" })).toBeInTheDocument();
  });

  it("shows an error with retry when the user cannot be loaded", async () => {
    renderApp("/home", "server-error");
    expect(await screen.findByRole("alert")).toHaveTextContent("Impossible d'afficher cette page");
    expect(screen.getByRole("button", { name: "Réessayer" })).toBeInTheDocument();
  });
});

describe("household area", () => {
  it("shows the four household tabs with the current one marked", async () => {
    const { container } = renderApp("/listings/42", "beneficiary");

    expect(await screen.findByRole("heading", { name: "Offre" })).toBeInTheDocument();
    expect(linkNames(mainNav())).toEqual(["Accueil", "Offres", "Réservations", "Profil"]);
    expect(within(mainNav()).getByRole("link", { name: "Offres" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByRole("link", { name: "Retour" })).toHaveAttribute("href", "/listings");
    await expectNoAxeViolations(container);
  });

  it("translates the tabs when the language changes", async () => {
    renderApp("/home", "beneficiary");
    await screen.findByRole("heading", { name: "Accueil" });
    await act(() => i18n.changeLanguage("en"));
    const nav = screen.getByRole("navigation", { name: "Main navigation" });
    expect(linkNames(nav)).toEqual(["Home", "Listings", "Reservations", "Profile"]);
  });
});

describe("store area", () => {
  it("shows the four store tabs and highlights Publier on the posting screen", async () => {
    const { container } = renderApp("/store/listings/new", "store_staff");

    expect(await screen.findByRole("heading", { name: "Publier une offre" })).toBeInTheDocument();
    expect(linkNames(mainNav())).toEqual(["Aujourd'hui", "Confirmer", "Publier", "Mes offres"]);
    expect(within(mainNav()).getByRole("link", { name: "Publier" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(within(mainNav()).getByRole("link", { name: "Mes offres" })).not.toHaveAttribute(
      "aria-current",
    );
    await expectNoAxeViolations(container);
  });

  it("offers the language switch in the account menu", async () => {
    renderApp("/store", "store_manager");
    await userEvent.click(await screen.findByRole("button", { name: "Mon compte" }));
    expect(await screen.findByText("Camille R.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("menuitem", { name: "English" }));
    expect(await screen.findByRole("heading", { name: "Today" })).toBeInTheDocument();
  });
});

describe("staff area", () => {
  it("shows intake workers only the screens they may use", async () => {
    renderApp("/staff", "intake_worker");

    expect(await screen.findByRole("heading", { name: "Foyers" })).toBeInTheDocument();
    expect(linkNames(staffNav())).toEqual(["Foyers", "Inscription en personne"]);
    expect(screen.getByText("Accès réservé au personnel autorisé")).toBeInTheDocument();
  });

  it("shows admins every staff screen and the signed-in name", async () => {
    const { container } = renderApp("/staff/partners", "admin");

    expect(await screen.findByRole("heading", { name: "Partenaires" })).toBeInTheDocument();
    expect(linkNames(staffNav())).toEqual([
      "Foyers",
      "Vérifications",
      "Inscription en personne",
      "Partenaires",
      "Commerces",
      "Catégories",
      "Journal d'audit",
    ]);
    expect(within(staffNav()).getByRole("link", { name: "Partenaires" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByText("Camille R.")).toBeInTheDocument();
    await expectNoAxeViolations(container);
  });
});
