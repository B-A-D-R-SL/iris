// AI contribution: 50% or more AI-generated
import { isValidElement, type ReactNode } from "react";
import { describe, expect, it } from "vitest";

import {
  EMPTY_CATEGORY,
  categoryErrors,
  fromCategory,
  serverErrors,
  toChanges,
  toNewCategory,
  type CategoryFormValues,
} from "./categoryForm";

function messageKey(error: ReactNode): string | null {
  if (!error) return null;
  if (isValidElement<{ messageKey: string }>(error)) return error.props.messageKey;
  throw new Error("Not a validation message");
}

const valid: CategoryFormValues = {
  code: "pet_food",
  nameFr: " Nourriture pour animaux ",
  nameEn: "Pet food",
  isFood: false,
  defaultValueCents: 600,
};

describe("categoryErrors", () => {
  it("accepts a complete category", () => {
    expect(categoryErrors(valid, { adding: true })).toEqual({});
  });

  it("requires every field when adding", () => {
    expect(Object.keys(categoryErrors(EMPTY_CATEGORY, { adding: true })).sort()).toEqual(
      ["code", "defaultValueCents", "nameEn", "nameFr"].sort(),
    );
  });

  it.each([
    ["pet_food", null],
    ["a1", null],
    ["Pet", "category.admin.codeError"],
    ["9lives", "category.admin.codeError"],
    ["pet-food", "category.admin.codeError"],
    ["x".repeat(65), "shared.validation.textMax"],
  ])("code %s -> %s", (code, expected) => {
    expect(messageKey(categoryErrors({ ...valid, code }, { adding: true }).code)).toBe(expected);
  });

  it("does not check the code when editing (it cannot change)", () => {
    expect(categoryErrors({ ...valid, code: "" }, { adding: false })).toEqual({});
  });

  it("refuses a negative value but leaves the maximum to the server", () => {
    expect(
      messageKey(
        categoryErrors({ ...valid, defaultValueCents: -1 }, { adding: true }).defaultValueCents,
      ),
    ).toBe("category.admin.valueError");
    expect(categoryErrors({ ...valid, defaultValueCents: 10_000_000 }, { adding: true })).toEqual(
      {},
    );
  });

  it("limits names to 150 characters", () => {
    expect(
      messageKey(categoryErrors({ ...valid, nameEn: "x".repeat(151) }, { adding: true }).nameEn),
    ).toBe("shared.validation.textMax");
  });
});

describe("payloads", () => {
  it("sends a new category trimmed and active", () => {
    expect(toNewCategory(valid)).toEqual({
      code: "pet_food",
      name_fr: "Nourriture pour animaux",
      name_en: "Pet food",
      is_food: false,
      default_value_cents: 600,
      is_active: true,
    });
  });

  it("never sends the code in an edit", () => {
    expect(toChanges(valid)).not.toHaveProperty("code");
  });

  it("reads a saved category back into the form", () => {
    expect(
      fromCategory({
        code: "bakery",
        name_fr: "Boulangerie",
        name_en: "Bakery",
        is_food: true,
        default_value_cents: 400,
        is_active: true,
      }),
    ).toEqual({
      code: "bakery",
      nameFr: "Boulangerie",
      nameEn: "Bakery",
      isFood: true,
      defaultValueCents: 400,
    });
  });
});

describe("serverErrors", () => {
  it("puts each API field's message on the matching form field", () => {
    expect(
      serverErrors({
        code: ["Ce code de catégorie existe déjà."],
        default_value_cents: ["Trop élevé."],
        non_field_errors: ["Autre."],
      }),
    ).toEqual({
      errors: { code: "Ce code de catégorie existe déjà.", defaultValueCents: "Trop élevé." },
      other: ["Autre."],
    });
  });
});
