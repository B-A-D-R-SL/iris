// AI contribution: 50% or more AI-generated
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import i18n from "../shared/i18n";
import { HomePage } from "./HomePage";

function renderHomePage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return render(
    <MantineProvider>
      <QueryClientProvider client={queryClient}>
        <HomePage />
      </QueryClientProvider>
    </MantineProvider>,
  );
}

describe("Iris homepage", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("fr");

    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ status: "ok" }),
      }),
    );
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("displays French by default", () => {
    renderHomePage();

    expect(screen.getByRole("heading", { name: "Bienvenue sur Iris" })).toBeInTheDocument();
  });

  it("switches from French to English", async () => {
    renderHomePage();

    await userEvent.click(screen.getByRole("button", { name: "English" }));

    expect(screen.getByRole("heading", { name: "Welcome to Iris" })).toBeInTheDocument();
  });

  it("shows connected when the backend responds", async () => {
    renderHomePage();

    expect(await screen.findByText("Connecté")).toBeInTheDocument();
  });

  it("shows unavailable when the backend fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("Connection failed")));

    renderHomePage();

    expect(await screen.findByText("Indisponible", {}, { timeout: 5000 })).toBeInTheDocument();
  });
});
