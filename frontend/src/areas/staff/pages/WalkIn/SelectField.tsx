// AI contribution: 50% or more AI-generated
import { Select } from "@mantine/core";
import { IconChevronDown } from "@tabler/icons-react";

import { useFieldWrapper, type BaseFieldProps } from "../../../../shared/forms";

export interface SelectFieldProps extends BaseFieldProps {
  value?: string | null;
  onChange: (value: string | null) => void;
  data: { value: string; label: string }[];
  placeholder?: string;
}

/** The Figma "Field" with a chevron: label above, 16 px value, error with icon. */
export function SelectField(props: SelectFieldProps) {
  const wrapper = useFieldWrapper(props);
  return (
    <Select
      {...wrapper}
      data={props.data}
      value={props.value || null}
      onChange={(value) => props.onChange(value)}
      placeholder={props.placeholder}
      allowDeselect={false}
      rightSection={<IconChevronDown size={20} stroke={2} aria-hidden />}
      rightSectionPointerEvents="none"
      disabled={props.disabled}
      name={props.name}
      id={props.id}
      onBlur={props.onBlur}
      onFocus={props.onFocus}
    />
  );
}
