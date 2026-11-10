// AI contribution: 50% or more AI-generated
import { Badge } from "@mantine/core";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";

import { logger } from "../logger";
import { statusTones, type StatusRecord, type StatusTone } from "./statusTones";
import { toneIcons } from "./toneIcons";

export interface StatusBadgeProps {
  record: StatusRecord;
  /** Accept future server values without crashing the screen. */
  status: string;
}

/** Render translated status meaning, with neutral fallback and scoped warning for unknown values. */
export function StatusBadge({ record, status }: StatusBadgeProps) {
  const { t } = useTranslation();
  const map: Readonly<Record<string, StatusTone>> = statusTones[record];
  const known = Object.hasOwn(map, status);
  const tone = known ? map[status] : "neutral";
  const Icon = tone === "neutral" ? null : toneIcons[tone];
  useEffect(() => {
    if (!known) logger.warning("unknown_status", { record, status });
  }, [known, record, status]);

  return (
    <Badge
      data-tone={tone}
      miw="max-content"
      leftSection={Icon ? <Icon size={14} stroke={2} aria-hidden /> : undefined}
      style={{
        color: `var(--iris-${tone}-strong)`,
        backgroundColor: `var(--iris-${tone}-light)`,
        textTransform: "none",
      }}
    >
      {known ? t(`shared.status.${record}.${status}`) : status}
    </Badge>
  );
}
