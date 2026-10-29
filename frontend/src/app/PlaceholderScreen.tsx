// AI contribution: 50% or more AI-generated
import { Title } from "@mantine/core";
import { IconTools } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";

import { EmptyState } from "../shared/ui";
import { AppBar } from "./layouts/AppBar";

interface PlaceholderScreenProps {
  titleKey: string;
  /** Household and store screens have an app bar; staff and public screens a heading. */
  appBar?: boolean;
  backTo?: string;
}

/** Stands in for a screen its story has not built yet; replace it in App.tsx. */
export function PlaceholderScreen({ titleKey, appBar = false, backTo }: PlaceholderScreenProps) {
  const { t } = useTranslation();
  const title = t(titleKey);
  return (
    <>
      {appBar ? (
        <AppBar title={title} backTo={backTo} />
      ) : (
        <Title order={1} mb="md">
          {title}
        </Title>
      )}
      <EmptyState
        icon={IconTools}
        title={t("app.placeholder.title")}
        description={t("app.placeholder.description")}
      />
    </>
  );
}
