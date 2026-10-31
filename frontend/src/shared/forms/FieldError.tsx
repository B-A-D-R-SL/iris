// AI contribution: 50% or more AI-generated
import { IconAlertCircle } from "@tabler/icons-react";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

import classes from "./fields.module.css";

/** Icon + bold message under a field: errors never rely on colour alone. */
export function FieldError({ children }: { children: ReactNode }) {
  return (
    <span className={classes.error}>
      <IconAlertCircle size={16} stroke={2} aria-hidden className={classes.errorIcon} />
      <span>{children}</span>
    </span>
  );
}

interface ValidationMessageProps {
  messageKey: string;
  values?: Record<string, unknown>;
}

/** An error that translates itself, so it follows the language switch. */
export function ValidationMessage({ messageKey, values }: ValidationMessageProps) {
  const { t } = useTranslation();
  return <FieldError>{t(messageKey, values)}</FieldError>;
}
