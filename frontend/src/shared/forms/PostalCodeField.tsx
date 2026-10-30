// AI contribution: 50% or more AI-generated
import { TextInput } from "@mantine/core";

import { useFieldWrapper, type BaseFieldProps } from "./fieldProps";
import { normalizePostalCode } from "./formats";

export interface PostalCodeFieldProps extends BaseFieldProps {
  /** Stored as uppercase with one space, for example "H2X 1Y4". */
  value?: string;
  onChange: (value: string) => void;
}

export function PostalCodeField(props: PostalCodeFieldProps) {
  const wrapper = useFieldWrapper(props);
  return (
    <TextInput
      {...wrapper}
      value={props.value ?? ""}
      onChange={(event) => props.onChange(normalizePostalCode(event.currentTarget.value))}
      placeholder="A1A 1A1"
      maxLength={7}
      autoComplete="postal-code"
      autoCapitalize="characters"
      spellCheck={false}
      disabled={props.disabled}
      name={props.name}
      id={props.id}
      onBlur={props.onBlur}
      onFocus={props.onFocus}
    />
  );
}
