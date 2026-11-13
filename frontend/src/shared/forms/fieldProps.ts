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

/**
 * The wrapper every shared field uses: label, helper and error wiring following
 * forms-and-fields.md, plus the props each field passes straight to its input.
 */
export function useFieldWrapper(props: BaseFieldProps) {
  const { label, optional, description, error } = props;
  const { t } = useTranslation();
  return {
    label: optional ? `${label} ${t("shared.form.optional")}` : label,
    description,
    // Server messages arrive as strings: give them the same icon + bold style.
    error: typeof error === "string" ? createElement(FieldError, null, error) : error,
    withAsterisk: false,
    inputWrapperOrder: INPUT_WRAPPER_ORDER,
    "aria-required": optional ? undefined : true,
    disabled: props.disabled,
    name: props.name,
    id: props.id,
    // Wrappers used just for labels must preserve existing form handlers.
    ...(props.onBlur === undefined ? {} : { onBlur: props.onBlur }),
    ...(props.onFocus === undefined ? {} : { onFocus: props.onFocus }),
  };
}
