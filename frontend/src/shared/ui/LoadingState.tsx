// AI contribution: 50% or more AI-generated
import { Center, Loader, Stack, Text } from "@mantine/core";
import { useTranslation } from "react-i18next";

/** Shown while a screen waits for the API; announced politely to screen readers. */
export function LoadingState({ label }: { label?: string }) {
  const { t } = useTranslation();
  return (
    <Center py="xl" role="status" aria-live="polite">
      <Stack align="center" gap="sm">
        <Loader aria-hidden />
        <Text size="sm" c="gray.7">
          {label ?? t("shared.states.loading")}
        </Text>
      </Stack>
    </Center>
  );
}
