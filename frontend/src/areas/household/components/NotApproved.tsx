// AI contribution: 50% or more AI-generated
import { Button } from "@mantine/core";
import { IconInfoCircle } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { EmptyState } from "../../../shared/ui";

/** H1.2a: only approved households see listings; the file's status is on /home. */
export function NotApproved() {
  const { t } = useTranslation();
  return (
    <EmptyState
      icon={IconInfoCircle}
      title={t("household.browse.notApprovedTitle")}
      description={t("household.browse.notApprovedDescription")}
      action={
        <Button component={Link} to="/home" variant="outline">
          {t("household.browse.fileStatus")}
        </Button>
      }
    />
  );
}
