// AI contribution: 50% or more AI-generated
/**
 * Values, checks and API mapping of the category form (US-35).
 * Only required fields and formats are checked here. The value limit comes from
 * the listing_posting rule setting, so the server checks it and its 400 message
 * appears under the field.
 */
import type { ReactNode } from "react";

import { allOf, hasLength, isRequired, validationMessage } from "../../shared/forms";
import type { CategoryChanges, StaffCategory } from "./adminApi";

export interface CategoryFormValues {
  /** Stable identifier: typed when adding, read-only when editing. */
  code: string;
  nameFr: string;
  nameEn: string;
  isFood: boolean;
  /** Integer cents, or null while empty. */
  defaultValueCents: number | null;
}

export const EMPTY_CATEGORY: CategoryFormValues = {
  code: "",
  nameFr: "",
  nameEn: "",
  isFood: false,
  defaultValueCents: null,
};

const CODE = /^[a-z][a-z0-9_]*$/;
const required = isRequired();
const name = allOf<string>(required, hasLength({ max: 150 }));

export function fromCategory(category: StaffCategory): CategoryFormValues {
  return {
    code: category.code,
    nameFr: category.name_fr,
    nameEn: category.name_en,
    isFood: category.is_food ?? false,
    defaultValueCents: category.default_value_cents ?? null,
  };
}

/** Errors of the form. The code is only checked when adding a category. */
export function categoryErrors(
  values: CategoryFormValues,
  { adding }: { adding: boolean },
): Record<string, ReactNode> {
  const errors: Record<string, ReactNode> = {};
  if (adding) {
    const codeError = allOf<string>(required, hasLength({ max: 64 }), (value) =>
      CODE.test(value.trim()) ? null : validationMessage("category.admin.codeError"),
    )(values.code);
    if (codeError) errors.code = codeError;
  }
  const nameFrError = name(values.nameFr);
  if (nameFrError) errors.nameFr = nameFrError;
  const nameEnError = name(values.nameEn);
  if (nameEnError) errors.nameEn = nameEnError;
  if (values.defaultValueCents === null) {
    errors.defaultValueCents = validationMessage("shared.validation.required");
  } else if (values.defaultValueCents < 0 || !Number.isSafeInteger(values.defaultValueCents)) {
    errors.defaultValueCents = validationMessage("category.admin.valueError");
  }
  return errors;
}

/** The POST body for a new category; new categories start active. */
export function toNewCategory(values: CategoryFormValues): StaffCategory {
  return {
    code: values.code.trim(),
    name_fr: values.nameFr.trim(),
    name_en: values.nameEn.trim(),
    is_food: values.isFood,
    default_value_cents: values.defaultValueCents ?? 0,
    is_active: true,
  };
}

/** The PATCH body for an edit; the code never changes. */
export function toChanges(values: CategoryFormValues): CategoryChanges {
  return {
    name_fr: values.nameFr.trim(),
    name_en: values.nameEn.trim(),
    is_food: values.isFood,
    default_value_cents: values.defaultValueCents ?? 0,
  };
}

const FORM_FIELD: Record<string, keyof CategoryFormValues> = {
  code: "code",
  name_fr: "nameFr",
  name_en: "nameEn",
  is_food: "isFood",
  default_value_cents: "defaultValueCents",
};

/** Splits a 400 response into field errors and the messages no field can show. */
export function serverErrors(fields: Record<string, string[]>) {
  const errors: Partial<Record<keyof CategoryFormValues, string>> = {};
  const other: string[] = [];
  for (const [apiField, messages] of Object.entries(fields)) {
    const field = FORM_FIELD[apiField];
    if (field) errors[field] = messages.join(" ");
    else other.push(...messages);
  }
  return { errors, other };
}
