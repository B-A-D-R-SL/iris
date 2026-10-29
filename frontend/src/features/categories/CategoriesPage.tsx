/**
 * AI contribution: 50% or more AI-generated
 * Read-only reference page for listing categories.
 */

import { Badge, Stack, Table, Text, Title } from "@mantine/core";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { EmptyState, ErrorState, LoadingState } from "../../shared/ui";
import { getCategories } from "./api";

export function CategoriesPage() {
  const { t, i18n } = useTranslation();

  const isEnglish = i18n.resolvedLanguage === "en";

  const { data, isPending, isError, refetch } = useQuery({
    queryKey: ["categories"],
    queryFn: getCategories,
  });

  const locale = isEnglish ? "en-CA" : "fr-CA";

  return (
    <Stack gap="md">
      <Title order={1}>{t("app.staffNav.categories")}</Title>

      <Text c="dimmed">{t("category.list.description")}</Text>

      {isPending ? (
        <LoadingState />
      ) : isError ? (
        <ErrorState onRetry={() => void refetch()} />
      ) : !data || data.length === 0 ? (
        <EmptyState
          title={t("category.list.empty")}
          description={t("category.list.emptyDescription")}
        />
      ) : (
        <Table.ScrollContainer minWidth={560}>
          <Table striped highlightOnHover withTableBorder>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>{t("category.list.name")}</Table.Th>
                <Table.Th>{t("category.list.code")}</Table.Th>
                <Table.Th>{t("category.list.type")}</Table.Th>
                <Table.Th>{t("category.list.defaultValue")}</Table.Th>
              </Table.Tr>
            </Table.Thead>

            <Table.Tbody>
              {data.map((category) => (
                <Table.Tr key={category.code}>
                  <Table.Td>{isEnglish ? category.name_en : category.name_fr}</Table.Td>

                  <Table.Td>
                    <Text size="sm" c="dimmed">
                      {category.code}
                    </Text>
                  </Table.Td>

                  <Table.Td>
                    <Badge variant="light" color={category.is_food ? "teal" : "gray"}>
                      {category.is_food ? t("category.list.food") : t("category.list.nonFood")}
                    </Badge>
                  </Table.Td>

                  <Table.Td>
                    {(category.default_value_cents / 100).toLocaleString(locale, {
                      style: "currency",
                      currency: "CAD",
                    })}
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      )}
    </Stack>
  );
}
