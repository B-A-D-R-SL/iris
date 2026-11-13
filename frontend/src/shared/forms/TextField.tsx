// AI contribution: 50% or more AI-generated
import { Textarea, TextInput } from "@mantine/core";
import type { ChangeEvent, ReactNode } from "react";

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

/** The helper text with the "0 / 500" counter at its end. */
function CountedHelp({ help, counter }: { help: ReactNode; counter: string }) {
  return (
    <span className={classes.helper}>
      <span>{help}</span>
      <span className={classes.counter}>{counter}</span>
    </span>
  );
}

export function TextField(props: TextFieldProps) {
  const { value = "", onChange, placeholder, maxLength, multiline = false, readOnly } = props;
  const counter = multiline && maxLength !== undefined ? `${value.length} / ${maxLength}` : null;
  const shared = {
    ...useFieldWrapper(props),
    description: counter ? (
      <CountedHelp help={props.description} counter={counter} />
    ) : (
      props.description
    ),
    value,
    placeholder,
    maxLength,
    readOnly,
    classNames: readOnly ? { input: classes.readOnly } : undefined,
  };
  const change = (event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    onChange(event.currentTarget.value);

  if (multiline) {
    return <Textarea {...shared} autosize minRows={3} onChange={change} />;
  }
  return (
    <TextInput
      {...shared}
      type={props.type ?? "text"}
      autoComplete={props.autoComplete}
      onChange={change}
    />
  );
}
