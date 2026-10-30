// AI contribution: 50% or more AI-generated
import { ActionIcon, NumberInput } from "@mantine/core";
import { IconMinus, IconPlus } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";

import { useFieldWrapper, type BaseFieldProps } from "./fieldProps";

export interface IntegerFieldProps extends BaseFieldProps {
  /** A whole number, or "" while the input is empty. */
  value?: number | string;
  onChange: (value: number | string) => void;
  min: number;
  max: number;
}

/**
 * A whole number with large − and + buttons, usable with one thumb
 * (forms-and-fields.md, type `integer`). Typing works too.
 */
export function IntegerField(props: IntegerFieldProps) {
  const { value = "", onChange, min, max } = props;
  const { t } = useTranslation();
  const wrapper = useFieldWrapper(props);
  const current = value === "" ? null : Number(value);
  const step = (delta: number) => {
    const next = current === null || Number.isNaN(current) ? min : current + delta;
    onChange(Math.min(max, Math.max(min, next)));
  };
  const button = (delta: -1 | 1) => (
    <ActionIcon
      variant="default"
      size={44}
      aria-label={t(delta < 0 ? "shared.integerField.decrease" : "shared.integerField.increase", {
        label: props.label,
      })}
      disabled={
        props.disabled || (current !== null && (delta < 0 ? current <= min : current >= max))
      }
      onClick={() => step(delta)}
    >
      {delta < 0 ? (
        <IconMinus size={20} stroke={2} aria-hidden />
      ) : (
        <IconPlus size={20} stroke={2} aria-hidden />
      )}
    </ActionIcon>
  );

  return (
    <NumberInput
      {...wrapper}
      value={value}
      onChange={onChange}
      min={min}
      max={max}
      allowDecimal={false}
      allowNegative={false}
      hideControls
      inputMode="numeric"
      leftSection={button(-1)}
      rightSection={button(1)}
      leftSectionWidth={44}
      rightSectionWidth={44}
      leftSectionPointerEvents="all"
      rightSectionPointerEvents="all"
      styles={{ input: { textAlign: "center" } }}
      disabled={props.disabled}
      name={props.name}
      id={props.id}
      onBlur={props.onBlur}
      onFocus={props.onFocus}
    />
  );
}
