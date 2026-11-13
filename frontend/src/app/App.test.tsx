// AI contribution: 50% or more AI-generated
import { act, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import type { Role } from "../shared/auth/roles";
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
  it("welcomes visitors with sign in, become a partner and the privacy policy", async () => {
    const { container } = renderApp("/", "signed-out");

    expect(await screen.findByRole("heading", { name: "Bienvenue sur Iris" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Connexion" })).toHaveAttribute("href", "/sign-in");
    expect(screen.getByRole("link", { name: "Devenir partenaire" })).toHaveAttribute(
      "href",
      "/partner/apply",
    );
    expect(screen.getByRole("link", { name: "Politique de confidentialité" })).toHaveAttribute(
      "href",
      "/privacy",
    );
    // Online sign-up adds its button with its screen (FIX-13).
    expect(screen.queryByRole("link", { name: "Inscrire mon foyer" })).not.toBeInTheDocument();
    await expectNoAxeViolations(container);
  });

  it("switches the whole page to English", async () => {
    renderApp("/", "signed-out");
    await userEvent.click(await screen.findByRole("button", { name: "English" }));
    expect(screen.getByRole("heading", { name: "Welcome to Iris" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Become a partner" })).toBeInTheDocument();
  });

  it.each([
    ["beneficiary", "Offres"],
    ["store_staff", "Publier une offre"],
    ["store_manager", "Publier une offre"],
    ["intake_worker", "Foyers"],
    ["admin", "Foyers"],
  ] as const)(
    "sends signed-in %s from the welcome page to their own area",
    async (role, heading) => {
      renderApp("/", role);
      expect(await screen.findByRole("heading", { name: heading })).toBeInTheDocument();
    },
  );

  it("explains an unknown address", async () => {
    renderApp("/nowhere", "signed-out");
    expect(await screen.findByRole("heading", { name: "Page introuvable" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Retour à l'accueil" })).toHaveAttribute("href", "/");
  });

  it("keeps the privacy page the partner form links to", async () => {
    renderApp("/privacy", "signed-out");
    expect(
      await screen.findByRole("heading", { name: "Politique de confidentialité" }),
    ).toBeInTheDocument();
  });
});

describe("screens not built yet have no route (FIX-13)", () => {
  it.each([
    ["/forgot-password", "signed-out"],
    ["/sign-up", "signed-out"],
    ["/home", "beneficiary"],
    ["/reservations", "beneficiary"],
    ["/profile", "beneficiary"],
    ["/store", "store_staff"],
    ["/store/confirm", "store_staff"],
    ["/store/listings", "store_manager"],
    ["/staff/review", "admin"],
    ["/staff/stores", "admin"],
  ] as const)("shows %s as not found", async (route, user) => {
    renderApp(route, user);
    expect(await screen.findByRole("heading", { name: "Page introuvable" })).toBeInTheDocument();
  });
});

describe("guards (deny by default)", () => {
  it.each(["/listings", "/store/listings/new", "/staff/households"])(
    "sends a signed-out visitor from %s to sign-in",
    async (route) => {
      renderApp(route, "signed-out");
      expect(await screen.findByRole("heading", { name: "Connexion" })).toBeInTheDocument();
    },
  );

  it.each([
    ["beneficiary", "/store/listings/new", "Offres"],
    ["beneficiary", "/staff/partners", "Offres"],
    ["store_staff", "/listings", "Publier une offre"],
    ["store_manager", "/staff/households", "Publier une offre"],
    ["intake_worker", "/store/listings/new", "Foyers"],
    ["admin", "/listings", "Foyers"],
  ] as const)("sends %s away from %s to their home (%s)", async (role, route, home) => {
    renderApp(route, role);
    expect(await screen.findByRole("heading", { name: home })).toBeInTheDocument();
  });

  it.each(["/staff/partners", "/staff/categories", "/staff/audit"])(
    "keeps admin-only %s from intake workers",
    async (route) => {
      renderApp(route, "intake_worker");
      expect(await screen.findByRole("heading", { name: "Foyers" })).toBeInTheDocument();
    },
  );

  it("shows an error with retry when the user cannot be loaded", async () => {
    renderApp("/listings", "server-error");
    expect(await screen.findByRole("alert")).toHaveTextContent("Impossible d'afficher cette page");
    expect(screen.getByRole("button", { name: "Réessayer" })).toBeInTheDocument();
  });
});

describe("household area", () => {
  it("shows the household tab marked on a listing detail", async () => {
    const { container } = renderApp("/listings/42", "beneficiary");

    expect(await screen.findByRole("heading", { name: "Offre" })).toBeInTheDocument();
    expect(linkNames(mainNav())).toEqual(["Offres"]);
    expect(within(mainNav()).getByRole("link", { name: "Offres" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByRole("link", { name: "Retour" })).toHaveAttribute("href", "/listings");
    await expectNoAxeViolations(container);
  });

  it("translates the tabs when the language changes", async () => {
    renderApp("/listings", "beneficiary");
    await screen.findByRole("heading", { name: "Offres" });
    await act(() => i18n.changeLanguage("en"));
    const nav = screen.getByRole("navigation", { name: "Main navigation" });
    expect(linkNames(nav)).toEqual(["Listings"]);
  });
});

describe("store area", () => {
  it("shows the store tab and highlights Publier on the posting screen", async () => {
    const { container } = renderApp("/store/listings/new", "store_staff");

    expect(await screen.findByRole("heading", { name: "Publier une offre" })).toBeInTheDocument();
    expect(linkNames(mainNav())).toEqual(["Publier"]);
    expect(within(mainNav()).getByRole("link", { name: "Publier" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    await expectNoAxeViolations(container);
  });

  it("offers the language switch in the account menu", async () => {
    renderApp("/store/listings/new", "store_manager");
    await userEvent.click(await screen.findByRole("button", { name: "Mon compte" }));
    expect(await screen.findByText("Camille R.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("menuitem", { name: "English" }));
    expect(await screen.findByRole("heading", { name: "Post a listing" })).toBeInTheDocument();
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
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

    expect(
      await screen.findByRole("heading", { name: "Demandes de partenariat" }),
    ).toBeInTheDocument();
    expect(linkNames(staffNav())).toEqual([
      "Foyers",
      "Inscription en personne",
      "Partenaires",
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

  it("closes the side menu after choosing a screen", async () => {
    renderApp("/staff/households", "intake_worker");
    await screen.findByRole("heading", { name: "Foyers" });
    await userEvent.click(screen.getByRole("button", { name: "Ouvrir le menu" }));
    expect(screen.getByRole("button", { name: "Fermer le menu" })).toBeInTheDocument();
    await userEvent.click(
      within(staffNav()).getByRole("link", { name: "Inscription en personne" }),
    );
    expect(await screen.findByRole("button", { name: "Ouvrir le menu" })).toBeInTheDocument();
  });
});
