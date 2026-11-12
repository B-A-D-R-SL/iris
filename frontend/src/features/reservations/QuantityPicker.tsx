// AI contribution: 50% or more AI-generated
/**
 * The quantity on the listing page (US-41), Figma H1.4 "Number stepper"
 * (component 8:185): label, then three boxes [−] [value] [+] 8 px apart, then
 * the helper. The shared IntegerField draws − and + inside the field, so this
 * composes the same Mantine parts to match the frame; the accessible names are
 * IntegerField's. Shown only when a household may take more than one. Its cap
 * is a convenience: the server checks the limits again.
 */
import { ActionIcon, Input, NumberInput } from "@mantine/core";
import { IconMinus, IconPlus } from "@tabler/icons-react";
import { useId } from "react";
import { useTranslation } from "react-i18next";

import { INPUT_WRAPPER_ORDER } from "../../shared/forms/fieldProps";
import { quantityToSend } from "./quantity";
import classes from "./QuantityPicker.module.css";

export interface QuantityPickerProps {
  /** A whole number, or "" while the field is being typed in. */
  value: number | string;
  maxPerHousehold: number;
  /** The most the picker allows: the household maximum or the units left, if fewer. */
  cap: number;
  onChange: (quantity: number | string) => void;
}

export function QuantityPicker({ value, maxPerHousehold, cap, onChange }: QuantityPickerProps) {
  const { t } = useTranslation();
  const id = useId();
  const label = t("reservation.reserve.quantity");
  const current = quantityToSend(value, cap);
  const step = (delta: -1 | 1) => (
    <ActionIcon
      variant="default"
      className={classes.step}
      aria-label={t(delta < 0 ? "shared.integerField.decrease" : "shared.integerField.increase", {
        label,
      })}
      disabled={delta < 0 ? current <= 1 : current >= cap}
      onClick={() => onChange(quantityToSend(current + delta, cap))}
    >
      {delta < 0 ? <IconMinus size={20} stroke={2} /> : <IconPlus size={20} stroke={2} />}
    </ActionIcon>
  );
  return (
    <Input.Wrapper
      id={id}
      label={label}
      description={t("reservation.reserve.quantityHelp", { max: maxPerHousehold })}
      inputWrapperOrder={INPUT_WRAPPER_ORDER}
      classNames={{ description: classes.help }}
    >
      <div className={classes.stepper}>
        {step(-1)}
        <NumberInput
          id={id}
          aria-describedby={`${id}-description`}
          classNames={{ root: classes.value, input: classes.input }}
          value={value}
          onChange={onChange}
          min={1}
          max={cap}
          allowDecimal={false}
          allowNegative={false}
          hideControls
          inputMode="numeric"
        />
        {step(1)}
      </div>
    </Input.Wrapper>
  );
}
