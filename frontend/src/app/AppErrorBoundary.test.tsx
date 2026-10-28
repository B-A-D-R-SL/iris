// AI contribution: 50% or more AI-generated
import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { renderWithProviders } from "../test/render";

function BrokenScreen(): never {
  throw new Error("Contains Samira's file number");
}

describe("AppErrorBoundary", () => {
  it("replaces a crashed screen with a plain message and logs no details", () => {
    vi.spyOn(console, "error").mockImplementation(() => {});

    renderWithProviders(<BrokenScreen />);

    expect(screen.getByRole("alert")).toHaveTextContent("Une erreur est survenue");
    expect(screen.getByRole("button", { name: "Recharger la page" })).toBeInTheDocument();
    const logged = vi.mocked(console.error).mock.calls.map((call) => String(call[0]));
    const ourEntry = logged.find((line) => line.includes("app_render_failed"));
    expect(ourEntry).toBeDefined();
    expect(ourEntry).not.toContain("Samira");
    vi.mocked(console.error).mockRestore();
  });
});
