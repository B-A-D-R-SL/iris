// AI contribution: 50% or more AI-generated
import { IconInfoCircle } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";

import { EmptyState } from "../../../shared/ui";

/**
 * H1.2a: only approved households see listings. The household home, which
 * shows the file's status, adds its link here when its story builds it.
 */
export function NotApproved() {
  const { t } = useTranslation();
  return (
    <EmptyState
      icon={IconInfoCircle}
      title={t("household.browse.notApprovedTitle")}
      description={t("household.browse.notApprovedDescription")}
    />
  );
}
