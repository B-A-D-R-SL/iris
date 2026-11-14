// AI contribution: 50% or more AI-generated
/// <reference types="node" />

import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

import { canonicalPostalCode, normalizePhone } from "./contact";
import { allOf, isPhone, isPostalCode, isRequired } from "./validators";

type ContactCase = { input: string; expected: string | null };
const cases = JSON.parse(
  readFileSync(
    resolve(
      dirname(fileURLToPath(import.meta.url)),
      "../../../../mock-data/validation/contact-values.json",
    ),
    "utf8",
  ),
) as Record<"phone" | "postal", ContactCase[]>;

describe("FIX-14 backend/frontend contact contract", () => {
  it.each(["", " \t", "\u0085", "\u001c", "\u0085\u001c"])(
    "keeps %j optional but refuses it for required contact fields",
    (value) => {
      expect(isPhone()(value)).toBeNull();
      expect(isPostalCode()(value)).toBeNull();
      expect(allOf(isRequired(), isPhone())(value)).not.toBeNull();
      expect(allOf(isRequired(), isPostalCode())(value)).not.toBeNull();
    },
  );

  it("does not treat an invisible non-whitespace marker as an empty contact", () => {
    expect(isPhone()("\ufeff")).not.toBeNull();
    expect(isPostalCode()("\ufeff")).not.toBeNull();
  });

  it.each(cases.phone)("normalizes and validates phone $input", ({ input, expected }) => {
    expect(normalizePhone(input)).toBe(expected);
    expect(isPhone()(input) === null).toBe(expected !== null);
    if (expected) expect(normalizePhone(expected)).toBe(expected);
  });

  it.each(cases.postal)("normalizes and validates postal code $input", ({ input, expected }) => {
    expect(canonicalPostalCode(input)).toBe(expected);
    expect(isPostalCode()(input) === null).toBe(expected !== null);
    if (expected) expect(canonicalPostalCode(expected)).toBe(expected);
  });
});
