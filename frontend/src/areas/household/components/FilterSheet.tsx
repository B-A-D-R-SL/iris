// AI contribution: 50% or more AI-generated
import { Drawer, Radio, Stack, Text } from "@mantine/core";
import type { MouseEvent } from "react";
import { useTranslation } from "react-i18next";

import classes from "../household.module.css";

export interface FilterGroup {
  /** A heading such as "Aliments"; leave it out for a single list. */
  label?: string;
  options: { value: string; label: string }[];
}

export interface FilterSheetProps {
  opened: boolean;
  onClose: () => void;
  title: string;
  /** The first choice, which removes the filter, for example "Toutes les catégories". */
  allLabel: string;
  groups: FilterGroup[];
  /** Shown instead of the groups when they are empty. */
  emptyText?: string;
  value: string | null;
  onChange: (value: string | null) => void;
}

const ALL = "";

/**
 * A bottom sheet with one choice per row (H1 step 3: like the store's category
 * picker). A tap chooses and closes; arrow keys only move the choice.
 */
export function FilterSheet(props: FilterSheetProps) {
  const { opened, onClose, title, allLabel, groups, emptyText, value, onChange } = props;
  const { t } = useTranslation();
  const choose = (choice: string) => onChange(choice === ALL ? null : choice);
  const closeOnTap = (event: MouseEvent) => {
    if (event.detail > 0) onClose();
  };
  const option = (choice: string, label: string) => (
    <Radio
      key={choice || "all"}
      value={choice}
      label={label}
      labelPosition="left"
      onClick={closeOnTap}
      classNames={{
        root: classes.option,
        body: classes.optionBody,
        labelWrapper: classes.optionLabel,
      }}
    />
  );

  return (
    <Drawer
      opened={opened}
      onClose={onClose}
      position="bottom"
      size="auto"
      title={title}
      closeButtonProps={{ "aria-label": t("household.browse.closeFilter") }}
      classNames={{ content: `${classes.palette} ${classes.sheet}` }}
    >
      <Stack gap="md">
        <Radio.Group value={value ?? ALL} onChange={choose} aria-label={title}>
          {option(ALL, allLabel)}
        </Radio.Group>
        {groups.length === 0 && emptyText && (
          <Text size="sm" c="gray.7">
            {emptyText}
          </Text>
        )}
        {groups.map((group, index) => (
          <Radio.Group
            key={group.label ?? index}
            label={group.label}
            aria-label={group.label ? undefined : title}
            value={value ?? ALL}
            onChange={choose}
          >
            <Stack gap={0} mt={group.label ? "xs" : 0}>
              {group.options.map((choice) => option(choice.value, choice.label))}
            </Stack>
          </Radio.Group>
        ))}
      </Stack>
    </Drawer>
  );
}
