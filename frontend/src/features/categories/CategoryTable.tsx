// AI contribution: 50% or more AI-generated
/** The category admin table (US-35): one row per category with its actions. */

import { Badge, Button, Group, Table, Text } from "@mantine/core";
import { IconPencil } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";

import { StatusBadge } from "../../shared/ui";
import type { StaffCategory } from "./adminApi";

const adminKey = "category.admin";

type CategoryActionsProps = {
  nameOf: (category: StaffCategory) => string;
  onEdit: (category: StaffCategory) => void;
  onDeactivate: (category: StaffCategory) => void;
  onReactivate: (category: StaffCategory) => void;
  /** The category whose reactivation is being sent, if any. */
  reactivatingCode: string | undefined;
};

type CategoryTableProps = CategoryActionsProps & {
  categories: StaffCategory[];
  locale: string;
};

export function CategoryTable({ categories, locale, ...actions }: CategoryTableProps) {
  const { t } = useTranslation();
  return (
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
          {categories.map((category) => (
            <CategoryRow key={category.code} category={category} locale={locale} {...actions} />
          ))}
        </Table.Tbody>
      </Table>
    </Table.ScrollContainer>
  );
}

function CategoryRow({
  category,
  locale,
  ...actions
}: CategoryActionsProps & { category: StaffCategory; locale: string }) {
  const { t } = useTranslation();
  return (
    <Table.Tr>
      <Table.Td>{actions.nameOf(category)}</Table.Td>
      <Table.Td>
        <Text size="sm" c="dimmed">
          {category.code}
        </Text>
      </Table.Td>
      <Table.Td>
        <Badge variant="light" color="neutral">
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
        <StatusBadge record="category" status={category.is_active ? "active" : "inactive"} />
      </Table.Td>
      <Table.Td>
        <CategoryActions category={category} {...actions} />
      </Table.Td>
    </Table.Tr>
  );
}

/** Edit, then deactivate (confirmed in a dialog) or reactivate (immediate). */
function CategoryActions({
  category,
  nameOf,
  onEdit,
  onDeactivate,
  onReactivate,
  reactivatingCode,
}: CategoryActionsProps & { category: StaffCategory }) {
  const { t } = useTranslation();
  const name = nameOf(category);
  return (
    <Group gap="xs" wrap="nowrap">
      <Button
        size="sm"
        variant="subtle"
        leftSection={<IconPencil size={16} stroke={2} aria-hidden />}
        aria-label={t(`${adminKey}.editName`, { name })}
        onClick={() => onEdit(category)}
      >
        {t(`${adminKey}.edit`)}
      </Button>
      {category.is_active ? (
        <Button
          size="sm"
          variant="outline"
          color="danger"
          aria-label={t(`${adminKey}.deactivateName`, { name })}
          onClick={() => onDeactivate(category)}
        >
          {t(`${adminKey}.deactivate`)}
        </Button>
      ) : (
        <Button
          size="sm"
          variant="outline"
          aria-label={t(`${adminKey}.reactivateName`, { name })}
          loading={reactivatingCode === category.code}
          onClick={() => onReactivate(category)}
        >
          {t(`${adminKey}.reactivate`)}
        </Button>
      )}
    </Group>
  );
}
