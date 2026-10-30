// AI contribution: 50% or more AI-generated
import { Textarea, TextInput } from "@mantine/core";

import { useFieldWrapper, type BaseFieldProps } from "./fieldProps";
import classes from "./fields.module.css";

export interface TextFieldProps extends BaseFieldProps {
  value?: string;
  onChange: (value: string) => void;
  placeholder?: string;
  maxLength?: number;
  /** Long text: a growing text area with a "0 / 500" counter when maxLength is set. */
  multiline?: boolean;
  readOnly?: boolean;
  type?: "text" | "email" | "url" | "search";
  autoComplete?: string;
}

export function TextField(props: TextFieldProps) {
  const {
    value = "",
    onChange,
    placeholder,
    maxLength,
    multiline = false,
    readOnly,
    type = "text",
    autoComplete,
  } = props;
  const wrapper = useFieldWrapper(props);
  const counter = multiline && maxLength !== undefined ? `${value.length} / ${maxLength}` : null;
  const description = counter ? (
    <span className={classes.helper}>
      <span>{props.description}</span>
      <span className={classes.counter}>{counter}</span>
    </span>
  ) : (
    props.description
  );
  const shared = {
    ...wrapper,
    description,
    value,
    placeholder,
    maxLength,
    readOnly,
    disabled: props.disabled,
    name: props.name,
    id: props.id,
    onBlur: props.onBlur,
    onFocus: props.onFocus,
    classNames: readOnly ? { input: classes.readOnly } : undefined,
  };

  if (multiline) {
    return (
      <Textarea
        {...shared}
        autosize
        minRows={3}
        onChange={(event) => onChange(event.currentTarget.value)}
      />
    );
  }
  return (
    <TextInput
      {...shared}
      type={type}
      autoComplete={autoComplete}
      onChange={(event) => onChange(event.currentTarget.value)}
    />
  );
}
