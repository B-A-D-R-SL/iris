// AI contribution: 50% or more AI-generated
import { Drawer, Group, Input, InputBase, Radio, Stack, Text } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { IconAlertTriangle, IconChevronDown } from "@tabler/icons-react";
import type { MouseEvent } from "react";
import { useTranslation } from "react-i18next";

import type { Category } from "../../../features/categories/api";
import { useFieldWrapper, type BaseFieldProps } from "../../../shared/forms";
import classes from "./CategoryPicker.module.css";

export interface CategoryPickerProps extends BaseFieldProps {
  categories: readonly Category[];
  /** The chosen category's code, or "" before a choice. */
  value?: string;
  onChange: (code: string) => void;
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
  const english = i18n.resolvedLanguage === "en";
  const nameOf = (category: Category) => (english ? category.name_en : category.name_fr);

  const sorted = [...categories].sort((a, b) =>
    nameOf(a).localeCompare(nameOf(b), english ? "en" : "fr"),
  );
  const groups = [
    { labelKey: "store.newListing.foodCategories", items: sorted.filter((c) => c.is_food) },
    { labelKey: "store.newListing.otherCategories", items: sorted.filter((c) => !c.is_food) },
  ].filter((group) => group.items.length > 0);
  const selected = categories.find((category) => category.code === value);

  // A tap closes the sheet; arrow keys only move the choice (their click has detail 0).
  const closeOnTap = (event: MouseEvent) => {
    if (event.detail > 0) close();
  };

  return (
    <>
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
        disabled={props.disabled}
        name={props.name}
        id={props.id}
        onBlur={props.onBlur}
        onFocus={props.onFocus}
      >
        {selected ? (
          nameOf(selected)
        ) : (
          <Input.Placeholder>{t("store.newListing.categoryPlaceholder")}</Input.Placeholder>
        )}
      </InputBase>

      <Drawer
        opened={opened}
        onClose={close}
        position="bottom"
        size="auto"
        title={props.label}
        closeButtonProps={{ "aria-label": t("store.newListing.closeCategories") }}
        classNames={{ content: classes.sheet }}
      >
        <Stack gap="md">
          <Group gap="xs" wrap="nowrap" align="flex-start">
            <IconAlertTriangle size={18} stroke={2} aria-hidden className={classes.noteIcon} />
            <Text size="sm">{t("store.newListing.prohibitedNote")}</Text>
          </Group>
          {groups.map((group) => (
            <Radio.Group
              key={group.labelKey}
              label={t(group.labelKey)}
              value={value}
              onChange={onChange}
            >
              <Stack gap={0} mt="xs">
                {group.items.map((category) => (
                  <Radio
                    key={category.code}
                    value={category.code}
                    label={nameOf(category)}
                    labelPosition="left"
                    onClick={closeOnTap}
                    classNames={{
                      root: classes.option,
                      body: classes.optionBody,
                      labelWrapper: classes.optionLabel,
                    }}
                  />
                ))}
              </Stack>
            </Radio.Group>
          ))}
        </Stack>
      </Drawer>
    </>
  );
}
