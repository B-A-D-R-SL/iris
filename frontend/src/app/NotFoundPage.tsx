// AI contribution: 50% or more AI-generated
import { Button } from "@mantine/core";
import { IconMapPinOff } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { EmptyState } from "../shared/ui";

export function NotFoundPage() {
  const { t } = useTranslation();
  return (
    <EmptyState
      icon={IconMapPinOff}
      title={t("app.notFound.title")}
      description={t("app.notFound.description")}
      action={
        <Button component={Link} to="/" variant="outline">
          {t("app.notFound.backHome")}
        </Button>
      }
    />
  );
}
