// AI contribution: 50% or more AI-generated
/**
 * Category management for admins (US-35): every category, active or not, with
 * add, edit, deactivate and reactivate. There is no delete: a deactivated
 * category disappears from the posting and partner forms, and existing
 * listings keep it.
 */

import { Button, Group, Stack, Text, Title } from "@mantine/core";
import { IconPlus } from "@tabler/icons-react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { EmptyState, ErrorState, LoadingState, Notice } from "../../shared/ui";
import { listStaffCategories, staffCategoriesKey } from "./adminApi";
import { CategoryDialog } from "./CategoryDialog";
import { CategoryTable } from "./CategoryTable";
import { DeactivateCategoryModal } from "./DeactivateCategoryModal";
import { useCategoryActions } from "./useCategoryActions";

const adminKey = "category.admin";

export function CategoriesPage() {
  const { t } = useTranslation();
  const actions = useCategoryActions();
  const { dialog, toDeactivate, outcome } = actions;

  return (
    <Stack gap="md">
      <Group justify="space-between" align="flex-start">
        <div>
          <Title order={1}>{t("app.staffNav.categories")}</Title>
          <Text c="dimmed">{t(`${adminKey}.description`)}</Text>
        </div>
        <Button leftSection={<IconPlus size={18} stroke={2} aria-hidden />} onClick={actions.add}>
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
      <CategoryList actions={actions} />
      {dialog && (
        <CategoryDialog
          category={dialog.mode === "edit" ? dialog.category : null}
          onClose={actions.closeDialog}
          onSaved={actions.saved}
        />
      )}
      {toDeactivate && (
        <DeactivateCategoryModal
          name={actions.nameOf(toDeactivate)}
          saving={actions.saving}
          onCancel={actions.cancelDeactivate}
          onConfirm={() => actions.deactivate(toDeactivate)}
        />
      )}
    </Stack>
  );
}

/** Every category, active or not, or the loading, error or empty state. */
function CategoryList({ actions }: { actions: ReturnType<typeof useCategoryActions> }) {
  const { t } = useTranslation();
  const { data, isPending, isError, refetch } = useQuery({
    queryKey: staffCategoriesKey,
    queryFn: () => listStaffCategories(actions.language),
  });

  if (isPending) return <LoadingState />;
  if (isError) return <ErrorState onRetry={() => void refetch()} />;
  if (data.length === 0) {
    return (
      <EmptyState
        title={t("category.list.empty")}
        description={t(`${adminKey}.emptyDescription`)}
      />
    );
  }
  return (
    <CategoryTable
      categories={data}
      locale={actions.locale}
      nameOf={actions.nameOf}
      onEdit={actions.edit}
      onDeactivate={actions.askToDeactivate}
      onReactivate={actions.reactivate}
      reactivatingCode={actions.reactivatingCode}
    />
  );
}
