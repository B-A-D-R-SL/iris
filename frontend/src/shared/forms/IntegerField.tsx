// AI contribution: 50% or more AI-generated
import { ActionIcon, NumberInput } from "@mantine/core";
import { IconMinus, IconPlus } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";

import { useFieldWrapper, type BaseFieldProps } from "./fieldProps";

export interface IntegerFieldProps extends BaseFieldProps {
  /** A whole number, or "" while the input is empty. */
  value?: number | string;
  onChange: (value: number | string) => void;
  min?: number;
  max?: number;
}

interface StepButtonProps {
  delta: -1 | 1;
  /** The field's label, read out with the button: "Diminuer (Quantité)". */
  label: string;
  disabled: boolean;
  onStep: (delta: -1 | 1) => void;
}

/** The large − or + button, 44 px for a thumb. */
function StepButton({ delta, label, disabled, onStep }: StepButtonProps) {
  const { t } = useTranslation();
  const Icon = delta < 0 ? IconMinus : IconPlus;
  return (
    <ActionIcon
      variant="default"
      size={44}
      aria-label={t(delta < 0 ? "shared.integerField.decrease" : "shared.integerField.increase", {
        label,
      })}
      disabled={disabled}
      onClick={() => onStep(delta)}
    >
      <Icon size={20} stroke={2} aria-hidden />
    </ActionIcon>
  );
}

/**
 * A whole number with large − and + buttons, usable with one thumb
 * (forms-and-fields.md, type `integer`). Typing works too.
 */
export function IntegerField(props: IntegerFieldProps) {
  const { value = "", onChange, min, max } = props;
  const current = value === "" ? null : Number(value);
  const step = (delta: number) => {
    const next = current === null || Number.isNaN(current) ? (min ?? 0) : current + delta;
    onChange(Math.min(max ?? Infinity, Math.max(min ?? -Infinity, next)));
  };
  const atLimit = (delta: -1 | 1) =>
    current !== null &&
    (delta < 0 ? min !== undefined && current <= min : max !== undefined && current >= max);
  const button = (delta: -1 | 1) => (
    <StepButton
      delta={delta}
      label={props.label}
      disabled={Boolean(props.disabled) || atLimit(delta)}
      onStep={step}
    />
  );

  return (
    <NumberInput
      {...useFieldWrapper(props)}
      value={value}
      onChange={onChange}
      min={min}
      max={max}
      allowDecimal={false}
      allowNegative={min === undefined || min < 0}
      hideControls
      inputMode="numeric"
      leftSection={button(-1)}
      rightSection={button(1)}
      leftSectionWidth={44}
      rightSectionWidth={44}
      leftSectionPointerEvents="all"
      rightSectionPointerEvents="all"
      styles={{ input: { textAlign: "center" } }}
    />
  );
}
