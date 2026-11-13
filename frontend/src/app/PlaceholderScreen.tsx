// AI contribution: 50% or more AI-generated
import { Title } from "@mantine/core";
import { IconTools } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";

import { EmptyState } from "../shared/ui";

/**
 * Only for /privacy (FIX-13): the partner application's consent text and the
 * welcome page link to the privacy policy, whose text does not exist yet. Every
 * other screen gets its route when its story builds it.
 */
export function PlaceholderScreen({ titleKey }: { titleKey: string }) {
  const { t } = useTranslation();
  return (
    <>
      <Title order={1} mb="md">
        {t(titleKey)}
      </Title>
      <EmptyState
        icon={IconTools}
        title={t("app.placeholder.title")}
        description={t("app.placeholder.description")}
      />
    </>
  );
}
