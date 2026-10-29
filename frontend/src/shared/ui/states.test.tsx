// AI contribution: 50% or more AI-generated
import { Button } from "@mantine/core";
import { act, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { expectNoAxeViolations, renderWithProviders } from "../../test/render";
import i18n from "../i18n";
import { EmptyState, ErrorState, LanguageSwitch, LoadingState, Notice } from "./index";

describe("LoadingState", () => {
  it("announces loading politely, in the current language", async () => {
    const { container } = renderWithProviders(<LoadingState />);
    expect(screen.getByRole("status")).toHaveTextContent("Chargement…");
    await act(() => i18n.changeLanguage("en"));
    expect(screen.getByRole("status")).toHaveTextContent("Loading…");
    await expectNoAxeViolations(container);
  });
});

describe("EmptyState", () => {
  it("says why it is empty and offers the next step", async () => {
    const { container } = renderWithProviders(
      <EmptyState
        title="Aucune offre pour ces filtres"
        description="Essayez un autre jour ou une autre catégorie."
        action={<Button variant="outline">Effacer les filtres</Button>}
      />,
    );
    expect(
      screen.getByRole("heading", { name: "Aucune offre pour ces filtres" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Essayez un autre jour ou une autre catégorie.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Effacer les filtres" })).toBeInTheDocument();
    await expectNoAxeViolations(container);
  });
});

describe("ErrorState", () => {
  it("explains the failure without technical details and retries on request", async () => {
    const onRetry = vi.fn();
    const { container } = renderWithProviders(<ErrorState onRetry={onRetry} />);

    expect(screen.getByRole("alert")).toHaveTextContent("Impossible d'afficher cette page");
    await userEvent.click(screen.getByRole("button", { name: "Réessayer" }));
    expect(onRetry).toHaveBeenCalledOnce();
    await expectNoAxeViolations(container);
  });

  it("has no retry button when nothing can be retried", () => {
    renderWithProviders(
      <ErrorState title="Accès refusé" description="Votre rôle ne permet pas cet accès." />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Accès refusé");
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});

describe("Notice", () => {
  it.each([
    ["info", "status"],
    ["success", "status"],
    ["warning", "status"],
    ["error", "alert"],
  ] as const)("a %s notice is announced as %s", (type, role) => {
    renderWithProviders(<Notice type={type} title="Vérifiez 4 champs." />);
    expect(screen.getByRole(role)).toHaveAttribute("data-type", type);
  });
});

describe("LanguageSwitch", () => {
  it("names the other language in that language and switches to it", async () => {
    renderWithProviders(<LanguageSwitch />);
    const button = screen.getByRole("button", { name: "English" });
    expect(button).toHaveAttribute("lang", "en");

    await userEvent.click(button);

    expect(i18n.resolvedLanguage).toBe("en");
    expect(document.documentElement.lang).toBe("en");
    expect(screen.getByRole("button", { name: "Français" })).toHaveAttribute("lang", "fr");
  });
});
