// AI contribution: 50% or more AI-generated
import { Stack, Text, Title } from "@mantine/core";
import { IconSearch, type TablerIcon } from "@tabler/icons-react";
import type { ReactNode } from "react";

export interface EmptyStateProps {
  title: string;
  /** Say plainly why it is empty and what to do next (wireframes H1 3a, W1 S10). */
  description?: ReactNode;
  icon?: TablerIcon;
  /** Usually one outline Button, for example "Effacer les filtres". */
  action?: ReactNode;
}

export function EmptyState({
  title,
  description,
  icon: Icon = IconSearch,
  action,
}: EmptyStateProps) {
  return (
    <Stack align="center" gap="xs" py="xl" px="md" ta="center">
      <Icon size={40} stroke={1.5} aria-hidden />
      <Title order={2} size="h3">
        {title}
      </Title>
      {description && (
        <Text size="sm" c="gray.7" maw={420}>
          {description}
        </Text>
      )}
      {action && (
        <Stack mt="sm" w="100%" maw={320}>
          {action}
        </Stack>
      )}
    </Stack>
  );
}
