// AI contribution: 50% or more AI-generated
import { TextInput } from "@mantine/core";

import { useFieldWrapper, type BaseFieldProps } from "./fieldProps";
import { formatPhone, phoneDigits, toPhoneValue } from "./formats";

export interface PhoneFieldProps extends BaseFieldProps {
  /** E.164 ("+15145550123") once 10 digits are typed; the typed digits before that. */
  value?: string;
  onChange: (value: string) => void;
}

/** A Canadian number shown as (514) 555-0123 and stored in E.164. */
export function PhoneField(props: PhoneFieldProps) {
  const wrapper = useFieldWrapper(props);
  return (
    <TextInput
      {...wrapper}
      type="tel"
      inputMode="tel"
      autoComplete="tel-national"
      placeholder="(514) 555-0123"
      value={formatPhone(phoneDigits(props.value ?? ""))}
      onChange={(event) => props.onChange(toPhoneValue(phoneDigits(event.currentTarget.value)))}
      disabled={props.disabled}
      name={props.name}
      id={props.id}
      onBlur={props.onBlur}
      onFocus={props.onFocus}
    />
  );
}
