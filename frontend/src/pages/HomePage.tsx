// AI contribution: 50% or more AI-generated
import { Badge, Button, Container, Group, Stack, Text, Title } from "@mantine/core";
import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { getHealthStatus } from "../shared/api/health";
import { logger } from "../shared/logger";

export function HomePage() {
  const { t, i18n } = useTranslation();

  const { isPending, isError } = useQuery({
    queryKey: ["backend-health"],
    queryFn: getHealthStatus,
    retry: 1,
    refetchInterval: 30000,
  });

  useEffect(() => {
    if (isError) logger.warning("backend_health_unavailable");
  }, [isError]);

  const switchLanguage = () => {
    const nextLanguage = i18n.resolvedLanguage === "fr" ? "en" : "fr";
    void i18n.changeLanguage(nextLanguage).then(() => {
      logger.info("language_changed");
    });
  };

  const status = isPending ? "checking" : isError ? "offline" : "online";

  const statusColor = status === "online" ? "green" : status === "offline" ? "red" : "gray";

  return (
    <Container size="md" py={80}>
      <Stack gap="lg">
        <Group justify="space-between">
          <Title order={2}>Iris</Title>
          <Button variant="outline" onClick={switchLanguage}>
            {t("language")}
          </Button>
        </Group>

        <Title order={1}>{t("title")}</Title>
        <Text size="lg">{t("description")}</Text>

        <Group gap="sm">
          <Text fw={500}>{t("backend.label")}:</Text>
          <Badge color={statusColor} variant="light">
            {t(`backend.${status}`)}
          </Badge>
        </Group>
      </Stack>
    </Container>
  );
}
