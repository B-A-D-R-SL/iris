// AI contribution: 50% or more AI-generated
import { screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { renderWithProviders } from "../test/render";

function BrokenScreen(): never {
  throw new Error("Contains Samira's file number");
}

const CONSOLE_METHODS = ["error", "warn", "info", "log", "debug"] as const;

afterEach(() => {
  vi.restoreAllMocks();
});

describe("AppErrorBoundary", () => {
  it("replaces a crashed screen with a plain message and logs no details", () => {
    const spies = CONSOLE_METHODS.map((method) =>
      vi.spyOn(console, method).mockImplementation(() => {}),
    );

    renderWithProviders(<BrokenScreen />);

    expect(screen.getByRole("alert")).toHaveTextContent("Une erreur est survenue");
    expect(screen.getByRole("button", { name: "Recharger la page" })).toBeInTheDocument();

    // Everything written to the console, by React or by us, as text.
    const output = spies
      .flatMap((spy) => spy.mock.calls.flat())
      .map((value) => (value instanceof Error ? `${value.message} ${value.stack}` : String(value)));
    expect(output.some((line) => line.includes("app_render_failed"))).toBe(true);
    expect(output.filter((line) => line.includes("Samira"))).toEqual([]);
  });
});
