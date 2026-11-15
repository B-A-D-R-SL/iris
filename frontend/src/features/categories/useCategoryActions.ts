// AI contribution: 50% or more AI-generated
/**
 * State and requests behind the category admin screen (US-35): which dialog is
 * open, the deactivate/reactivate request, and the message shown afterwards.
 */

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { CategoryFailed, staffCategoriesKey, updateCategory, type StaffCategory } from "./adminApi";

export type CategoryDialogState =
  { mode: "add" } | { mode: "edit"; category: StaffCategory } | null;
export type CategoryOutcome = { type: "success" | "error"; message: string };

const adminKey = "category.admin";

/** The admin list and the public (posting form) list both change after a save. */
function useRefreshCategories() {
  const queryClient = useQueryClient();
  return () => {
    void queryClient.invalidateQueries({ queryKey: staffCategoriesKey });
    void queryClient.invalidateQueries({ queryKey: ["categories"] });
  };
}

/** Deactivate or reactivate a category, then report the outcome and which category it was. */
function useSetActive(
  nameOf: (category: StaffCategory) => string,
  report: (outcome: CategoryOutcome, code: string) => void,
) {
  const { t, i18n } = useTranslation();
  const refresh = useRefreshCategories();
  return useMutation({
    mutationFn: ({ category, active }: { category: StaffCategory; active: boolean }) =>
      updateCategory(
        category.code,
        { is_active: active },
        i18n.resolvedLanguage === "en" ? "en" : "fr",
      ),
    onSuccess: (category) => {
      const done = category.is_active ? "reactivated" : "deactivated";
      const message = t(`${adminKey}.${done}`, { name: nameOf(category) });
      report({ type: "success", message }, category.code);
      refresh();
    },
    onError: (error, { category }) => {
      const message =
        error instanceof CategoryFailed
          ? error.message || t(`${adminKey}.saveError`)
          : t(`${adminKey}.networkError`);
      report({ type: "error", message }, category.code);
    },
  });
}

export function useCategoryActions() {
  const { t, i18n } = useTranslation();
  const isEnglish = i18n.resolvedLanguage === "en";
  const refresh = useRefreshCategories();
  const [dialog, setDialog] = useState<CategoryDialogState>(null);
  const [toDeactivate, setToDeactivate] = useState<StaffCategory | null>(null);
  const [outcome, setOutcome] = useState<CategoryOutcome | null>(null);

  const nameOf = (category: StaffCategory) => (isEnglish ? category.name_en : category.name_fr);
  const setActive = useSetActive(nameOf, (result, code) => {
    // Close the confirmation only if it is for the category that finished: a
    // reactivation ending must not close another category's open confirmation.
    setToDeactivate((current) => (current?.code === code ? null : current));
    setOutcome(result);
  });
  /** Starting an action clears the message left by the previous one. */
  const start = (action: () => void) => {
    setOutcome(null);
    action();
  };

  return {
    language: isEnglish ? ("en" as const) : ("fr" as const),
    locale: isEnglish ? "en-CA" : "fr-CA",
    nameOf,
    dialog,
    toDeactivate,
    outcome,
    saving: setActive.isPending,
    reactivatingCode: setActive.isPending ? setActive.variables?.category.code : undefined,
    add: () => start(() => setDialog({ mode: "add" })),
    edit: (category: StaffCategory) => start(() => setDialog({ mode: "edit", category })),
    askToDeactivate: (category: StaffCategory) => start(() => setToDeactivate(category)),
    reactivate: (category: StaffCategory) =>
      start(() => setActive.mutate({ category, active: true })),
    deactivate: (category: StaffCategory) => setActive.mutate({ category, active: false }),
    closeDialog: () => setDialog(null),
    cancelDeactivate: () => setToDeactivate(null),
    saved: (category: StaffCategory) => {
      setDialog(null);
      setOutcome({ type: "success", message: t(`${adminKey}.saved`, { name: nameOf(category) }) });
      refresh();
    },
  };
}
