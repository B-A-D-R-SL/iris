// AI contribution: 50% or more AI-generated
/**
 * Validation rules for the shared fields, ready for @mantine/form:
 *
 *   useForm({ validate: { phone: allOf(isRequired(), isPhone()) } })
 *
 * A rule returns null when the value is fine, or a message element that
 * translates itself (French or English) under the field. Empty values pass
 * every rule except isRequired, so optional fields stay optional.
 */
import { createElement, type ReactNode } from "react";

import { ValidationMessage } from "./FieldError";
import { centsToDollars } from "./formats";

export type Rule<T> = (value: T) => ReactNode;

const POSTAL_CODE = /^[A-Z]\d[A-Z] \d[A-Z]\d$/;
const E164_CANADA = /^\+1[2-9]\d{9}$/;
const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const BYTES_PER_MB = 1024 * 1024;

export function validationMessage(messageKey: string, values?: Record<string, unknown>): ReactNode {
  return createElement(ValidationMessage, { messageKey, values });
}

function isEmpty(value: unknown): boolean {
  return (
    value === null || value === undefined || (typeof value === "string" && value.trim() === "")
  );
}

/** "YYYY-MM-DD" that exists on the calendar: Date would turn 2026-02-31 into March 3. */
function isCalendarDate(value: string): boolean {
  if (!ISO_DATE.test(value)) return false;
  const [year, month, day] = value.split("-").map(Number);
  const date = new Date(Date.UTC(year, month - 1, day));
  return (
    date.getUTCFullYear() === year && date.getUTCMonth() === month - 1 && date.getUTCDate() === day
  );
}

/** Runs rules in order and returns the first error. */
export function allOf<T>(...rules: Rule<T>[]): Rule<T> {
  return (value) => {
    for (const rule of rules) {
      const error = rule(value);
      if (error) return error;
    }
    return null;
  };
}

export function isRequired(): Rule<unknown> {
  return (value) => (isEmpty(value) ? validationMessage("shared.validation.required") : null);
}

export function isEmail(): Rule<string> {
  return (value) =>
    isEmpty(value) || EMAIL.test(value.trim())
      ? null
      : validationMessage("shared.validation.email");
}

export function hasLength({ min = 0, max }: { min?: number; max: number }): Rule<string> {
  return (value) => {
    if (isEmpty(value)) return null;
    const length = value.trim().length;
    if (length >= min && length <= max) return null;
    return min > 0
      ? validationMessage("shared.validation.textLength", { min, max })
      : validationMessage("shared.validation.textMax", { max });
  };
}

export function isPostalCode(): Rule<string> {
  return (value) =>
    isEmpty(value) || POSTAL_CODE.test(value)
      ? null
      : validationMessage("shared.validation.postalCode");
}

/** PhoneField gives E.164 once 10 digits are typed; anything else is incomplete. */
export function isPhone(): Rule<string> {
  return (value) =>
    isEmpty(value) || E164_CANADA.test(value) ? null : validationMessage("shared.validation.phone");
}

export function isMoneyInRange({
  minCents = 0,
  maxCents,
}: {
  minCents?: number;
  maxCents: number;
}): Rule<number | null> {
  return (value) => {
    if (value === null || (value >= minCents && value <= maxCents)) return null;
    return validationMessage("shared.validation.moneyRange", {
      min: centsToDollars(minCents),
      max: centsToDollars(maxCents),
    });
  };
}

/** Dates are "YYYY-MM-DD" strings, so they compare correctly as text. */
export function isDateInRange({ min, max }: { min?: string; max?: string } = {}): Rule<
  string | null
> {
  return (value) => {
    if (isEmpty(value) || value === null) return null;
    if (!isCalendarDate(value)) {
      return validationMessage("shared.validation.date");
    }
    if (min && value < min) return validationMessage("shared.validation.dateMin", { date: min });
    if (max && value > max) return validationMessage("shared.validation.dateMax", { date: max });
    return null;
  };
}

export function isAcceptedFile({
  types,
  maxMb,
}: {
  types: readonly string[];
  maxMb?: number;
}): Rule<File | null> {
  return (file) => {
    if (file === null) return null;
    if (!types.includes(file.type)) {
      return validationMessage("shared.validation.fileType", { types: fileTypeNames(types) });
    }
    if (maxMb !== undefined && file.size > maxMb * BYTES_PER_MB) {
      return validationMessage("shared.validation.fileSize", { max: maxMb });
    }
    return null;
  };
}

/** ["image/jpeg", "application/pdf"] -> "JPG, PDF" for messages and hints. */
export function fileTypeNames(types: readonly string[]): string {
  return types
    .map((type) => (type === "image/jpeg" ? "JPG" : (type.split("/")[1] ?? type).toUpperCase()))
    .join(", ");
}
