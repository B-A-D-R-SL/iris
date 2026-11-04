// AI contribution: 50% or more AI-generated
import { Button, Checkbox, Group, Modal, Stack } from "@mantine/core";
import { useForm } from "@mantine/form";
import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { MoneyField, TextField } from "../../shared/forms";
import { Notice } from "../../shared/ui";
import { CategoryFailed, createCategory, updateCategory, type StaffCategory } from "./adminApi";
import {
  EMPTY_CATEGORY,
  categoryErrors,
  fromCategory,
  serverErrors,
  toChanges,
  toNewCategory,
  type CategoryFormValues,
} from "./categoryForm";

type CategoryDialogProps = {
  /** The category being edited, or null to add a new one. */
  category: StaffCategory | null;
  onClose: () => void;
  onSaved: (category: StaffCategory) => void;
};

/** Add or edit a category in a dialog (US-35). The code is read-only when editing. */
export function CategoryDialog({ category, onClose, onSaved }: CategoryDialogProps) {
  const { t, i18n } = useTranslation();
  const language = i18n.resolvedLanguage === "en" ? "en" : "fr";
  const adding = category === null;
  const adminKey = "category.admin";

  const form = useForm<CategoryFormValues>({
    initialValues: category ? fromCategory(category) : EMPTY_CATEGORY,
  });
  const [problem, setProblem] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: (values: CategoryFormValues) =>
      adding
        ? createCategory(toNewCategory(values), language)
        : updateCategory(category.code, toChanges(values), language),
    onSuccess: onSaved,
    onError: (error) => {
      if (error instanceof CategoryFailed && error.status === 400) {
        const { errors, other } = serverErrors(error.fields);
        form.setErrors(errors);
        setProblem(other.length > 0 ? other.join(" ") : null);
      } else if (error instanceof CategoryFailed) {
        setProblem(error.message || t(`${adminKey}.saveError`));
      } else {
        setProblem(t(`${adminKey}.networkError`));
      }
    },
  });

  const save = () => {
    setProblem(null);
    const errors = categoryErrors(form.values, { adding });
    if (Object.keys(errors).length > 0) {
      form.setErrors(errors);
      return;
    }
    form.clearErrors();
    mutation.mutate(form.values);
  };

  return (
    <Modal
      opened
      onClose={onClose}
      title={t(`${adminKey}.${adding ? "addTitle" : "editTitle"}`)}
      size="lg"
    >
      <form
        noValidate
        onSubmit={(event) => {
          event.preventDefault();
          save();
        }}
      >
        <Stack gap="md">
          {problem && (
            <Notice type="error" title={t(`${adminKey}.notSaved`)}>
              {problem}
            </Notice>
          )}

          <TextField
            {...form.getInputProps("code")}
            label={t("category.list.code")}
            description={t(`${adminKey}.${adding ? "codeHelp" : "codeLocked"}`)}
            readOnly={!adding}
            maxLength={64}
            autoComplete="off"
          />

          <TextField
            {...form.getInputProps("nameFr")}
            label={t(`${adminKey}.nameFr`)}
            maxLength={150}
            autoComplete="off"
          />

          <TextField
            {...form.getInputProps("nameEn")}
            label={t(`${adminKey}.nameEn`)}
            maxLength={150}
            autoComplete="off"
          />

          <Checkbox
            {...form.getInputProps("isFood", { type: "checkbox" })}
            size="md"
            label={t(`${adminKey}.isFood`)}
            description={t(`${adminKey}.isFoodHelp`)}
          />

          <MoneyField
            {...form.getInputProps("defaultValueCents")}
            label={t("category.list.defaultValue")}
            description={t(`${adminKey}.defaultValueHelp`)}
          />

          <Group justify="flex-end" gap="sm">
            <Button variant="subtle" onClick={onClose}>
              {t(`${adminKey}.cancel`)}
            </Button>
            <Button type="submit" loading={mutation.isPending}>
              {t(`${adminKey}.save`)}
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}
