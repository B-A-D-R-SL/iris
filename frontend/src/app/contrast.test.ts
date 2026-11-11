// AI contribution: 50% or more AI-generated
import { describe, expect, it } from "vitest";

import { contrastRatio } from "./contrast";
import { referenceColors, tokens } from "./tokens";

describe("WCAG 2.1 contrast (NFR-03)", () => {
  it("returns 21 for black and white in either order", () => {
    expect(contrastRatio(referenceColors.black, referenceColors.white)).toBe(21);
    expect(contrastRatio(referenceColors.white, referenceColors.black)).toBe(21);
  });

  it.each(Object.entries(tokens))("returns 1 for %s on itself", (_name, color) => {
    expect(contrastRatio(color, color)).toBe(1);
  });

  it.each(["transparent", "rgb(0, 0, 0)", "invalid", "#fff"])("rejects unsupported %s", (color) => {
    expect(() => contrastRatio(color, tokens.surface)).toThrow(TypeError);
    expect(() => contrastRatio(tokens.surface, color)).toThrow(TypeError);
  });
});

const textPairs = [
  ["text", "defaultHover"],
  ["neutralHover", "neutralLightHover"],
  ["infoHover", "infoLightHover"],
  ["dangerHover", "dangerLightHover"],
  ["warningHover", "warningLightHover"],
  ["successHover", "successLightHover"],
  ["primaryHover", "primaryLightHover"],
  ["onPrimary", "neutralHover"],
  ["onPrimary", "infoHover"],
  ["onPrimary", "dangerHover"],
  ["onPrimary", "warningHover"],
  ["onPrimary", "successHover"],
  ["onPrimary", "neutralStrong"],
  ["onPrimary", "infoStrong"],
  ["onPrimary", "warningStrong"],
  ["onPrimary", "successStrong"],
  ["text", "surface"],
  ["text", "surfaceRaised"],
  ["textMuted", "surface"],
  ["textMuted", "surfaceRaised"],
  ["onPrimary", "primary"],
  ["onPrimary", "primaryHover"],
  ["onPrimary", "primaryPressed"],
  ["onPrimary", "dangerStrong"],
  ["textPlaceholder", "surface"],
  ["dangerStrong", "surface"],
  ["dangerStrong", "surfaceRaised"],
  ["text", "primaryLight"],
  ["primary", "primaryLight"],
  ["neutralStrong", "neutralLight"],
  ["successStrong", "successLight"],
  ["successStrong", "surface"],
  ["warningStrong", "warningLight"],
  ["warningStrong", "surface"],
  ["dangerStrong", "dangerLight"],
  ["infoStrong", "infoLight"],
] as const;

describe("Iris semantic contrast", () => {
  it.each(textPairs)("%s on %s meets 4.5:1 for normal text", (text, background) => {
    expect(contrastRatio(tokens[text], tokens[background])).toBeGreaterThanOrEqual(4.5);
  });

  it.each([
    ["inputBorder", "surface"],
    ["inputBorder", "surfaceRaised"],
    ["primary", "surface"],
    ["primary", "surfaceRaised"],
  ] as const)("%s on %s meets 3:1 for controls", (foreground, background) => {
    expect(contrastRatio(tokens[foreground], tokens[background])).toBeGreaterThanOrEqual(3);
  });
});
