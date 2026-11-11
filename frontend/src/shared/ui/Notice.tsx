// AI contribution: 50% or more AI-generated
import { Alert } from "@mantine/core";
import type { ReactNode } from "react";

import classes from "./Notice.module.css";
import { toneIcons } from "./toneIcons";

export type NoticeType = "info" | "success" | "warning" | "error";

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
  const Icon = toneIcons[type === "error" ? "danger" : type];
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
