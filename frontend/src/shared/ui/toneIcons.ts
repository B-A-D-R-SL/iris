// AI contribution: 50% or more AI-generated
import {
  IconAlertCircle,
  IconAlertTriangle,
  IconCircleCheck,
  IconInfoCircle,
  type TablerIcon,
} from "@tabler/icons-react";

import type { StatusTone } from "./statusTones";

/** Notices and status badges use the same non-colour cues. */
export const toneIcons: Record<Exclude<StatusTone, "neutral">, TablerIcon> = {
  info: IconInfoCircle,
  success: IconCircleCheck,
  warning: IconAlertTriangle,
  danger: IconAlertCircle,
};
