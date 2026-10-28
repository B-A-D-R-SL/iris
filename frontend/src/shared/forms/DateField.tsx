// AI contribution: 50% or more AI-generated
import { DateInput } from "@mantine/dates";
import { IconCalendar } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";

import "../i18n/dates";
import { useFieldWrapper, type BaseFieldProps } from "./fieldProps";

export interface DateFieldProps extends BaseFieldProps {
  /** "YYYY-MM-DD", or null when empty. */
  value?: string | null;
  onChange: (value: string | null) => void;
  minDate?: string;
  maxDate?: string;
}

/** A calendar date typed or picked as YYYY-MM-DD (forms-and-fields.md, type `date`). */
export function DateField(props: DateFieldProps) {
  const { t } = useTranslation();
  const wrapper = useFieldWrapper(props);
  return (
    <DateInput
      {...wrapper}
      value={props.value ?? null}
      onChange={props.onChange}
      minDate={props.minDate}
      maxDate={props.maxDate}
      valueFormat="YYYY-MM-DD"
      placeholder={t("shared.dateField.placeholder")}
      rightSection={<IconCalendar size={20} stroke={2} aria-hidden />}
      rightSectionPointerEvents="none"
      disabled={props.disabled}
      name={props.name}
      id={props.id}
      onBlur={props.onBlur}
      onFocus={props.onFocus}
    />
  );
}
