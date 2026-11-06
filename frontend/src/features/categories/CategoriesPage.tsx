/**
 * AI contribution: 50% or more AI-generated
 * Category management for admins (US-35): every category, active or not, with
 * add, edit, deactivate and reactivate. There is no delete: a deactivated
 * category disappears from the posting and partner forms, and existing
 * listings keep it.
 */

import { Badge, Button, Group, Modal, Stack, Table, Text, Title } from "@mantine/core";
import { IconPencil, IconPlus } from "@tabler/icons-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { EmptyState, ErrorState, LoadingState, Notice } from "../../shared/ui";
import {
  CategoryFailed,
  listStaffCategories,
  staffCategoriesKey,
  updateCategory,
  type StaffCategory,
} from "./adminApi";
import { CategoryDialog } from "./CategoryDialog";

type Dialog = { mode: "add" } | { mode: "edit"; category: StaffCategory } | null;
type Outcome = { type: "success" | "error"; message: string } | null;

export function CategoriesPage() {
  const { t, i18n } = useTranslation();
  const queryClient = useQueryClient();

  const isEnglish = i18n.resolvedLanguage === "en";
  const language = isEnglish ? "en" : "fr";
  const locale = isEnglish ? "en-CA" : "fr-CA";
  const adminKey = "category.admin";

  const [dialog, setDialog] = useState<Dialog>(null);
  const [toDeactivate, setToDeactivate] = useState<StaffCategory | null>(null);
  const [outcome, setOutcome] = useState<Outcome>(null);

  const { data, isPending, isError, refetch } = useQuery({
    queryKey: staffCategoriesKey,
    queryFn: () => listStaffCategories(language),
  });

  const nameOf = (category: StaffCategory) => (isEnglish ? category.name_en : category.name_fr);

  /** The admin list and the public (posting form) list both change. */
  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: staffCategoriesKey });
    void queryClient.invalidateQueries({ queryKey: ["categories"] });
  };

  const activeMutation = useMutation({
    mutationFn: ({ category, active }: { category: StaffCategory; active: boolean }) =>
      updateCategory(category.code, { is_active: active }, language),
    onSuccess: (category) => {
      setToDeactivate(null);
      setOutcome({
        type: "success",
        message: t(`${adminKey}.${category.is_active ? "reactivated" : "deactivated"}`, {
          name: nameOf(category),
        }),
      });
      refresh();
    },
    onError: (error) => {
      setToDeactivate(null);
      setOutcome({
        type: "error",
        message:
          error instanceof CategoryFailed
            ? error.message || t(`${adminKey}.saveError`)
            : t(`${adminKey}.networkError`),
      });
    },
  });

  const saved = (category: StaffCategory) => {
    setDialog(null);
    setOutcome({ type: "success", message: t(`${adminKey}.saved`, { name: nameOf(category) }) });
    refresh();
  };

  return (
    <Stack gap="md">
      <Group justify="space-between" align="flex-start">
        <div>
          <Title order={1}>{t("app.staffNav.categories")}</Title>
          <Text c="dimmed">{t(`${adminKey}.description`)}</Text>
        </div>
        <Button
          leftSection={<IconPlus size={18} stroke={2} aria-hidden />}
          onClick={() => {
            setOutcome(null);
            setDialog({ mode: "add" });
          }}
        >
          {t(`${adminKey}.add`)}
        </Button>
      </Group>

      {outcome && (
        <Notice
          type={outcome.type}
          title={t(`${adminKey}.${outcome.type === "success" ? "done" : "notSaved"}`)}
        >
          {outcome.message}
        </Notice>
      )}

      {isPending ? (
        <LoadingState />
      ) : isError ? (
        <ErrorState onRetry={() => void refetch()} />
      ) : !data || data.length === 0 ? (
        <EmptyState
          title={t("category.list.empty")}
          description={t(`${adminKey}.emptyDescription`)}
        />
      ) : (
        <Table.ScrollContainer minWidth={760}>
          <Table striped highlightOnHover withTableBorder>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>{t("category.list.name")}</Table.Th>
                <Table.Th>{t("category.list.code")}</Table.Th>
                <Table.Th>{t("category.list.type")}</Table.Th>
                <Table.Th>{t("category.list.defaultValue")}</Table.Th>
                <Table.Th>{t(`${adminKey}.status`)}</Table.Th>
                <Table.Th>{t(`${adminKey}.actions`)}</Table.Th>
              </Table.Tr>
            </Table.Thead>

            <Table.Tbody>
              {data.map((category) => (
                <Table.Tr key={category.code}>
                  <Table.Td>{nameOf(category)}</Table.Td>

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

                  <Table.Td>
                    <Badge variant={category.is_active ? "filled" : "outline"} color="gray">
                      {t(`${adminKey}.${category.is_active ? "active" : "inactive"}`)}
                    </Badge>
                  </Table.Td>

                  <Table.Td>
                    <Group gap="xs" wrap="nowrap">
                      <Button
                        size="sm"
                        variant="subtle"
                        leftSection={<IconPencil size={16} stroke={2} aria-hidden />}
                        aria-label={t(`${adminKey}.editName`, { name: nameOf(category) })}
                        onClick={() => {
                          setOutcome(null);
                          setDialog({ mode: "edit", category });
                        }}
                      >
                        {t(`${adminKey}.edit`)}
                      </Button>
                      {category.is_active ? (
                        <Button
                          size="sm"
                          variant="outline"
                          aria-label={t(`${adminKey}.deactivateName`, { name: nameOf(category) })}
                          onClick={() => {
                            setOutcome(null);
                            setToDeactivate(category);
                          }}
                        >
                          {t(`${adminKey}.deactivate`)}
                        </Button>
                      ) : (
                        <Button
                          size="sm"
                          variant="outline"
                          aria-label={t(`${adminKey}.reactivateName`, { name: nameOf(category) })}
                          loading={
                            activeMutation.isPending &&
                            activeMutation.variables?.category.code === category.code
                          }
                          onClick={() => {
                            setOutcome(null);
                            activeMutation.mutate({ category, active: true });
                          }}
                        >
                          {t(`${adminKey}.reactivate`)}
                        </Button>
                      )}
                    </Group>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      )}

      {dialog && (
        <CategoryDialog
          category={dialog.mode === "edit" ? dialog.category : null}
          onClose={() => setDialog(null)}
          onSaved={saved}
        />
      )}

      {toDeactivate && (
        <Modal
          opened
          onClose={() => setToDeactivate(null)}
          title={t(`${adminKey}.confirmTitle`, { name: nameOf(toDeactivate) })}
        >
          <Stack gap="md">
            <Text>{t(`${adminKey}.confirmBody`)}</Text>
            <Group justify="flex-end" gap="sm">
              <Button variant="subtle" onClick={() => setToDeactivate(null)}>
                {t(`${adminKey}.cancel`)}
              </Button>
              <Button
                loading={activeMutation.isPending}
                onClick={() => activeMutation.mutate({ category: toDeactivate, active: false })}
              >
                {t(`${adminKey}.deactivate`)}
              </Button>
            </Group>
          </Stack>
        </Modal>
      )}
    </Stack>
  );
}
