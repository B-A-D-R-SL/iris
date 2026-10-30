// AI contribution: 50% or more AI-generated
import { createElement, type ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { FieldError } from "./FieldError";

/** Helper text sits under the input, like the Figma "Field" component. */
export const INPUT_WRAPPER_ORDER: ("label" | "input" | "description" | "error")[] = [
  "label",
  "input",
  "description",
  "error",
];

/** Props every shared field accepts; @mantine/form's getInputProps() fills value, onChange, error and focus. */
export interface BaseFieldProps {
  label: string;
  /** Fields are required unless marked optional; the label then ends with "(facultatif)". */
  optional?: boolean;
  description?: ReactNode;
  error?: ReactNode;
  disabled?: boolean;
  name?: string;
  id?: string;
  onBlur?: () => void;
  onFocus?: () => void;
}

/** Label, helper and error wiring shared by the fields, following forms-and-fields.md. */
export function useFieldWrapper({ label, optional, description, error }: BaseFieldProps) {
  const { t } = useTranslation();
  return {
    label: optional ? `${label} ${t("shared.form.optional")}` : label,
    description,
    // Server messages arrive as strings: give them the same icon + bold style.
    error: typeof error === "string" ? createElement(FieldError, null, error) : error,
    withAsterisk: false,
    inputWrapperOrder: INPUT_WRAPPER_ORDER,
    "aria-required": optional ? undefined : true,
  };
}
