// AI contribution: 50% or more AI-generated
import { NumberInput, type NumberInputProps } from "@mantine/core";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { useFieldWrapper, type BaseFieldProps } from "./fieldProps";
import { centsToDollars, dollarsToCents } from "./formats";

export interface MoneyFieldProps extends BaseFieldProps {
  /** Integer cents (Rule: money is integer cents), or null when empty. */
  value?: number | null;
  onChange: (value: number | null) => void;
  allowNegative?: boolean;
}

type InputValue = number | string;
type ValueChange = NonNullable<NumberInputProps["onValueChange"]>;

const toInput = (cents: number | null): InputValue => (cents === null ? "" : centsToDollars(cents));

/** Dollars and cents, shown as 0,00 $ in French and $0.00 in English, stored as cents. */
export function MoneyField(props: MoneyFieldProps) {
  const { i18n } = useTranslation();
  const french = i18n.resolvedLanguage !== "en";
  const wrapper = useFieldWrapper(props);

  // The input keeps what is being typed ("12,"); cents go out only from parsed numbers.
  const value = props.value ?? null;
  const [input, setInput] = useState<InputValue>(toInput(value));
  const [lastValue, setLastValue] = useState(value);
  if (value !== lastValue) {
    // Changed from outside (for example a form reset): show the new amount.
    setLastValue(value);
    setInput(toInput(value));
  }

  const handleValueChange: ValueChange = ({ floatValue }, { source }) => {
    if (source !== "event") return;
    const cents = floatValue === undefined ? null : dollarsToCents(floatValue);
    setLastValue(cents);
    props.onChange(cents);
  };

  return (
    <NumberInput
      {...wrapper}
      value={input}
      onChange={setInput}
      onValueChange={handleValueChange}
      decimalScale={2}
      fixedDecimalScale
      allowNegative={props.allowNegative ?? false}
      hideControls
      inputMode="decimal"
      thousandSeparator={french ? " " : ","}
      decimalSeparator={french ? "," : "."}
      prefix={french ? undefined : "$"}
      suffix={french ? " $" : undefined}
      placeholder={french ? "0,00 $" : "$0.00"}
      disabled={props.disabled}
      name={props.name}
      id={props.id}
      onBlur={props.onBlur}
      onFocus={props.onFocus}
    />
  );
}
