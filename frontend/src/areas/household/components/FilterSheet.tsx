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

interface FilterOptionGroupProps {
  group: FilterGroup;
  /** Names a group without a heading for screen readers. */
  title: string;
  value: string;
  onChange: (choice: string) => void;
  onTap: (event: MouseEvent) => void;
}

/** One radio group of full-width rows, with its heading when it has one. */
function FilterOptionGroup({ group, title, value, onChange, onTap }: FilterOptionGroupProps) {
  return (
    <Radio.Group
      label={group.label}
      aria-label={group.label ? undefined : title}
      value={value}
      onChange={onChange}
    >
      <Stack gap={0} mt={group.label ? "xs" : 0}>
        {group.options.map((option) => (
          <Radio
            key={option.value || "all"}
            value={option.value}
            label={option.label}
            labelPosition="left"
            onClick={onTap}
            classNames={{
              root: classes.option,
              body: classes.optionBody,
              labelWrapper: classes.optionLabel,
            }}
          />
        ))}
      </Stack>
    </Radio.Group>
  );
}

/**
 * A bottom sheet with one choice per row (H1 step 3: like the store's category
 * picker). A tap chooses and closes; arrow keys only move the choice.
 */
export function FilterSheet(props: FilterSheetProps) {
  const { opened, onClose, title, allLabel, groups, emptyText, value, onChange } = props;
  const { t } = useTranslation();
  const groupProps = {
    title,
    value: value ?? ALL,
    onChange: (choice: string) => onChange(choice === ALL ? null : choice),
    onTap: (event: MouseEvent) => {
      if (event.detail > 0) onClose();
    },
  };

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
        <FilterOptionGroup group={{ options: [{ value: ALL, label: allLabel }] }} {...groupProps} />
        {groups.length === 0 && emptyText && (
          <Text size="sm" c="gray.7">
            {emptyText}
          </Text>
        )}
        {groups.map((group, index) => (
          <FilterOptionGroup key={group.label ?? index} group={group} {...groupProps} />
        ))}
      </Stack>
    </Drawer>
  );
}
