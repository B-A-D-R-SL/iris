// AI contribution: 50% or more AI-generated
import { Button, Stack, Text, Title } from "@mantine/core";
import { IconAlertTriangle } from "@tabler/icons-react";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

export interface ErrorStateProps {
  title?: string;
  description?: ReactNode;
  /** Shows "Réessayer" when the failed request can simply be sent again. */
  onRetry?: () => void;
  /** Another way out, for example a link back to a list. */
  action?: ReactNode;
}

/** A failed load or a refused screen; never shows technical details (wireframe W1 S22). */
export function ErrorState({ title, description, onRetry, action }: ErrorStateProps) {
  const { t } = useTranslation();
  return (
    <Stack align="center" gap="xs" py="xl" px="md" ta="center" role="alert">
      <IconAlertTriangle size={40} stroke={1.5} aria-hidden />
      <Title order={2} size="h3">
        {title ?? t("shared.states.errorTitle")}
      </Title>
      <Text size="sm" c="gray.7" maw={420}>
        {description ?? t("shared.states.errorDescription")}
      </Text>
      {(onRetry || action) && (
        <Stack mt="sm" w="100%" maw={320}>
          {onRetry && <Button onClick={onRetry}>{t("shared.states.retry")}</Button>}
          {action}
        </Stack>
      )}
    </Stack>
  );
}
