/**
 * AI contribution: 50% or more AI-generated
 * Tests for the Categories reference page.
 */

import { act, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import App from "../../app/App";
import i18n from "../../shared/i18n";
import { renderWithProviders, testUser } from "../../test/render";
import { CategoriesPage } from "./CategoriesPage";

const bakery = {
  code: "bakery",
  name_fr: "Boulangerie",
  name_en: "Bakery",
  is_food: true,
  default_value_cents: 400,
};

describe("CategoriesPage", () => {
  it("displays categories in French by default", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json([bakery])));

    renderWithProviders(<CategoriesPage />);

    expect(await screen.findByText("Boulangerie")).toBeInTheDocument();
    expect(screen.getByText("bakery")).toBeInTheDocument();
    expect(screen.getByText("Alimentaire")).toBeInTheDocument();
  });

  it("switches category names to English", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json([bakery])));

    renderWithProviders(<CategoriesPage />);

    expect(await screen.findByText("Boulangerie")).toBeInTheDocument();

    await act(async () => {
      await i18n.changeLanguage("en");
    });

    expect(screen.getByText("Bakery")).toBeInTheDocument();
    expect(screen.getByText("Food")).toBeInTheDocument();
    expect(screen.queryByText("Boulangerie")).not.toBeInTheDocument();
  });

  it("displays a loading indicator while fetching", () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => new Promise<Response>(() => {})),
    );

    renderWithProviders(<CategoriesPage />);

    expect(screen.getByRole("status")).toHaveTextContent("Chargement");
  });

  it("displays an empty state when there are no categories", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json([])));

    renderWithProviders(<CategoriesPage />);

    expect(
      await screen.findByRole("heading", {
        name: "Aucune catégorie disponible",
      }),
    ).toBeInTheDocument();

    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("displays an error and supports retry", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(null, { status: 503 }))
      .mockResolvedValueOnce(Response.json([bakery]));

    vi.stubGlobal("fetch", fetchMock);

    renderWithProviders(<CategoriesPage />);

    expect(await screen.findByRole("alert")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Réessayer" }));

    expect(await screen.findByText("Boulangerie")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("renders inside the existing admin route", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;

      if (url.endsWith("/api/me/")) {
        return Response.json(testUser("admin"));
      }

      if (url.endsWith("/api/categories/")) {
        return Response.json([bakery]);
      }

      return new Response(null, { status: 404 });
    });

    vi.stubGlobal("fetch", fetchMock);

    renderWithProviders(<App />, {
      route: "/staff/categories",
    });

    expect(await screen.findByText("Boulangerie")).toBeInTheDocument();

    expect(screen.getByRole("heading", { name: "Catégories" })).toBeInTheDocument();
  });
});
