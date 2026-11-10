// AI contribution: 50% or more AI-generated
import { Button, TextInput, DEFAULT_THEME, mergeMantineTheme } from "@mantine/core";
import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { renderWithProviders } from "../test/render";
import { theme, cssVariablesResolver } from "./theme";
import { palettes, tokens } from "./tokens";

describe("Iris theme (Figma Components page)", () => {
  it("uses iris for filled buttons and the danger token for errors", () => {
    renderWithProviders(<Button variant="filled">Publish</Button>);
    expect(screen.getByRole("button")).toHaveAttribute("data-variant", "filled");
    expect(screen.getByRole("button").getAttribute("style")).toContain("--iris-primary");
    const resolved = mergeMantineTheme(DEFAULT_THEME, theme);
    expect(resolved.primaryColor).toBe("iris");
    expect(resolved.colors.iris).toEqual(palettes.iris);
    const variables = cssVariablesResolver(resolved);
    expect(variables.light["--mantine-color-error"]).toBe("var(--iris-danger-strong)");
    expect(variables.variables["--iris-danger-strong"]).toBe(tokens.dangerStrong);
    expect(variables.light["--mantine-color-dimmed"]).toBe("var(--iris-text-muted)");
    expect(variables.light["--mantine-color-placeholder"]).toBe("var(--iris-text-placeholder)");
  });

  it.each([
    ["danger", "filled", "background", "var(--iris-danger-strong)"],
    ["warning", "light", "background", "var(--iris-warning-light)"],
    ["info", "light", "color", "var(--iris-info-strong)"],
    ["neutral", "light", "color", "var(--iris-neutral-strong)"],
    ["iris", "filled", "hover", "var(--iris-primary-hover)"],
    ["iris", "outline", "border", "1px solid var(--iris-primary)"],
  ])("resolves %s %s %s from semantic tokens", (color, variant, property, value) => {
    const resolved = mergeMantineTheme(DEFAULT_THEME, theme);
    const colors = resolved.variantColorResolver({ theme: resolved, color, variant });
    expect(colors[property as keyof typeof colors]).toBe(value);
  });

  it("makes default buttons 48 px tall with 16 px text", () => {
    renderWithProviders(<Button>Publier</Button>);
    const style = screen.getByRole("button", { name: "Publier" }).getAttribute("style") ?? "";
    expect(style).toContain("--button-height: calc(3rem");
    expect(style).toContain("--button-fz: calc(1rem");
  });

  it("keeps compact buttons compact when asked", () => {
    renderWithProviders(<Button size="xs">Retirer</Button>);
    const style = screen.getByRole("button", { name: "Retirer" }).getAttribute("style") ?? "";
    expect(style).not.toContain("--button-height: calc(3rem");
  });

  it("makes inputs 44 px tall with 16 px text so iOS does not zoom", () => {
    renderWithProviders(<TextInput label="Titre" />);
    const wrapper = screen.getByLabelText("Titre").parentElement;
    expect(wrapper).toHaveAttribute("data-size", "md");
    expect(wrapper?.getAttribute("style")).toContain("--input-height: calc(2.75rem");
    expect(wrapper?.getAttribute("style")).toContain("--input-fz: calc(1rem");
  });
});
