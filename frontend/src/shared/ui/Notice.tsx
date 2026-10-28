// AI contribution: 50% or more AI-generated
import { Alert } from "@mantine/core";
import {
  IconAlertCircle,
  IconAlertTriangle,
  IconCircleCheck,
  IconInfoCircle,
  type TablerIcon,
} from "@tabler/icons-react";
import type { ReactNode } from "react";

import classes from "./Notice.module.css";

export type NoticeType = "info" | "success" | "warning" | "error";

const ICONS: Record<NoticeType, TablerIcon> = {
  info: IconInfoCircle,
  success: IconCircleCheck,
  warning: IconAlertTriangle,
  error: IconAlertCircle,
};

export interface NoticeProps {
  type?: NoticeType;
  title?: ReactNode;
  children?: ReactNode;
}

/**
 * The Figma "Alert": the type is carried by the icon and the title, not colour;
 * errors get a 2 px border. Errors are announced at once (role="alert").
 */
export function Notice({ type = "info", title, children }: NoticeProps) {
  const Icon = ICONS[type];
  return (
    <Alert
      icon={<Icon size={20} stroke={2} aria-hidden />}
      title={title}
      className={classes.notice}
      data-type={type}
      role={type === "error" ? "alert" : "status"}
    >
      {children}
    </Alert>
  );
}
