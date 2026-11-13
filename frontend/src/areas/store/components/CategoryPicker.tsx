// AI contribution: 50% or more AI-generated
import { Drawer, Group, Input, InputBase, Radio, Stack, Text } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { IconAlertTriangle, IconChevronDown } from "@tabler/icons-react";
import type { MouseEvent } from "react";
import { useTranslation } from "react-i18next";

import type { Category } from "../../../features/categories/api";
import { useFieldWrapper, type BaseFieldProps } from "../../../shared/forms";
import classes from "./CategoryPicker.module.css";
import { ProhibitedItemsLink } from "./ProhibitedItemsLink";

export interface CategoryPickerProps extends BaseFieldProps {
  categories: readonly Category[];
  /** The chosen category's code, or "" before a choice. */
  value?: string;
  onChange: (code: string) => void;
}

interface CategoryGroup {
  labelKey: string;
  items: Category[];
}

/** Categories by name in the current language, food first; empty groups left out. */
function useCategoryGroups(categories: readonly Category[]) {
  const { i18n } = useTranslation();
  const english = i18n.resolvedLanguage === "en";
  const nameOf = (category: Category) => (english ? category.name_en : category.name_fr);
  const sorted = [...categories].sort((a, b) =>
    nameOf(a).localeCompare(nameOf(b), english ? "en" : "fr"),
  );
  const groups: CategoryGroup[] = [
    { labelKey: "store.newListing.foodCategories", items: sorted.filter((c) => c.is_food) },
    { labelKey: "store.newListing.otherCategories", items: sorted.filter((c) => !c.is_food) },
  ].filter((group) => group.items.length > 0);
  return { groups, nameOf };
}

interface CategorySheetProps {
  opened: boolean;
  onClose: () => void;
  title: string;
  categories: readonly Category[];
  value: string;
  onChange: (code: string) => void;
}

/** SET-11 "Category sheet" note: 12/16 gray text, 16 px icon, 6 px gap. */
function ProhibitedNote() {
  const { t } = useTranslation();
  return (
    <Group gap={6} wrap="nowrap" align="flex-start">
      <IconAlertTriangle size={16} stroke={2} aria-hidden className={classes.noteIcon} />
      <Text size="xs" c="dimmed">
        {t("store.newListing.prohibitedNote")} <ProhibitedItemsLink short />
      </Text>
    </Group>
  );
}

interface CategoryRadioGroupProps {
  group: CategoryGroup;
  nameOf: (category: Category) => string;
  value: string;
  onChange: (code: string) => void;
  onTap: (event: MouseEvent) => void;
}

/** One group ("Aliments" or "Autres produits") with a full-width row per category. */
function CategoryRadioGroup({ group, nameOf, value, onChange, onTap }: CategoryRadioGroupProps) {
  const { t } = useTranslation();
  const option = {
    root: classes.option,
    body: classes.optionBody,
    labelWrapper: classes.optionLabel,
  };
  return (
    <Radio.Group label={t(group.labelKey)} value={value} onChange={onChange}>
      <Stack gap={0} mt="xs">
        {group.items.map((category) => (
          <Radio
            key={category.code}
            value={category.code}
            label={nameOf(category)}
            labelPosition="left"
            onClick={onTap}
            classNames={option}
          />
        ))}
      </Stack>
    </Radio.Group>
  );
}

/** The bottom sheet: the prohibited-items note, then one radio row per category. */
function CategorySheet(props: CategorySheetProps) {
  const { opened, onClose, title, categories, value, onChange } = props;
  const { t } = useTranslation();
  const { groups, nameOf } = useCategoryGroups(categories);
  // A tap closes the sheet; arrow keys only move the choice (their click has detail 0).
  const closeOnTap = (event: MouseEvent) => {
    if (event.detail > 0) onClose();
  };

  return (
    <Drawer
      opened={opened}
      onClose={onClose}
      position="bottom"
      size="auto"
      title={title}
      closeButtonProps={{ "aria-label": t("store.newListing.closeCategories") }}
      classNames={{ content: classes.sheet }}
    >
      <Stack gap="md">
        <ProhibitedNote />
        {groups.map((group) => (
          <CategoryRadioGroup
            key={group.labelKey}
            group={group}
            nameOf={nameOf}
            value={value}
            onChange={onChange}
            onTap={closeOnTap}
          />
        ))}
      </Stack>
    </Drawer>
  );
}

/**
 * The category field: a bottom sheet with food first (SET-11, "Category picker").
 * Prohibited items have no category, so they cannot be posted (US-34).
 */
export function CategoryPicker(props: CategoryPickerProps) {
  const { categories, value = "", onChange } = props;
  const { t, i18n } = useTranslation();
  const [opened, { open, close }] = useDisclosure(false);
  const wrapper = useFieldWrapper(props);
  const selected = categories.find((category) => category.code === value);
  const name = selected && (i18n.resolvedLanguage === "en" ? selected.name_en : selected.name_fr);

  return (
    <>
      {/* A button, so not aria-required: the label and the error still come from the wrapper. */}
      <InputBase
        component="button"
        type="button"
        pointer
        label={wrapper.label}
        description={wrapper.description}
        error={wrapper.error}
        withAsterisk={false}
        inputWrapperOrder={wrapper.inputWrapperOrder}
        rightSection={<IconChevronDown size={20} stroke={2} aria-hidden />}
        rightSectionPointerEvents="none"
        aria-haspopup="dialog"
        onClick={open}
        disabled={wrapper.disabled}
        name={wrapper.name}
        id={wrapper.id}
        onBlur={wrapper.onBlur}
        onFocus={wrapper.onFocus}
      >
        {name ?? <Input.Placeholder>{t("store.newListing.categoryPlaceholder")}</Input.Placeholder>}
      </InputBase>
      <CategorySheet
        opened={opened}
        onClose={close}
        title={props.label}
        categories={categories}
        value={value}
        onChange={onChange}
      />
    </>
  );
}
