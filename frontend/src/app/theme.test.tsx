// AI contribution: 50% or more AI-generated
import { Button, TextInput } from "@mantine/core";
import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { renderWithProviders } from "../test/render";

describe("Iris theme (Figma Components page)", () => {
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
